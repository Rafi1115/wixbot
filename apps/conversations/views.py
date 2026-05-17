import time
import uuid as uuid_lib

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bots.models import Bot
from apps.knowledge.rag import get_ai_response
from .models import Conversation, Message
from .serializers import (
    AgentMessageSerializer,
    ChatRequestSerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    HumanHandoffSerializer,
    MessageSerializer,
)


# ─────────────────────────────────────────────
# Public Chat Endpoint — used by the JS widget
# ─────────────────────────────────────────────

class ChatView(APIView):
    """
    POST /api/chat/
    No auth required — called from the JS widget embedded on any website.
    Identifies the bot via bot_id (the tenant token in the widget script tag).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 1 — Find the bot
        try:
            bot = Bot.objects.select_related("tenant").prefetch_related("behaviors").get(
                id=data["bot_id"], widget_enabled=True
            )
        except Bot.DoesNotExist:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)

        # 2 — Check message limit
        if not bot.is_within_message_limit():
            return Response(
                {"reply": "This chatbot has reached its monthly message limit. Please try again next month."},
                status=status.HTTP_200_OK,
            )

        # 3 — Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            session_id=data["session_id"],
            defaults={
                "bot": bot,
                "channel": "website",
                "customer_name": data.get("customer_name", ""),
                "customer_email": data.get("customer_email", ""),
                "customer_ip": self._get_client_ip(request),
            },
        )

        # 4 — Save user message
        user_message = data["message"]
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message,
        )

        # 5 — Human handoff mode — don't reply with AI
        if conversation.mode == "human":
            return Response({
                "reply": None,
                "session_id": str(conversation.id),
                "handoff": True,
                "handoff_message": "You are now connected with a human agent.",
            })

        # 6 — Build chat history for context (last 6 messages)
        history = list(
            conversation.messages.order_by("-created_at")
                .values("role", "content")[:6]
        )
        history.reverse()
        history = [{"role": m["role"] if m["role"] != "agent" else "assistant", "content": m["content"]} for m in history]

        # 7 — Build behavior instructions
        behaviors = bot.behaviors.all().values_list("instruction", flat=True)
        behavior_text = "\n".join(f"- {b}" for b in behaviors)

        # 8 — Get AI response and measure time
        start = time.time()
        reply = get_ai_response(
            question=user_message,
            bot_id=str(bot.id),
            business_context=bot.business_context,
            behavior_instructions=behavior_text,
            chat_history=history,
        )
        response_time = round(time.time() - start, 2)

        # 9 — Save assistant message
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=reply,
            response_time_seconds=response_time,
        )

        # 10 — Increment usage counter
        bot.increment_messages()

        # 11 — Update last_message_at
        Conversation.objects.filter(pk=conversation.pk).update(last_message_at=timezone.now())

        # 12 — Check for lead capture signal
        self._maybe_capture_lead(reply, conversation)

        return Response({
            "reply": reply,
            "session_id": str(conversation.id),
            "handoff": False,
        })

    def _get_client_ip(self, request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def _maybe_capture_lead(self, reply, conversation):
        """
        If AI reply contains the LEAD_CAPTURED signal, parse and save the lead.
        Signal format: LEAD_CAPTURED::Name::Email::Phone
        """
        if "LEAD_CAPTURED::" not in reply:
            return
        try:
            from apps.leads.models import Lead
            parts = reply.split("::")
            Lead.objects.get_or_create(
                conversation=conversation,
                defaults={
                    "bot": conversation.bot,
                    "name": parts[1].strip() if len(parts) > 1 else "",
                    "email": parts[2].strip() if len(parts) > 2 else "",
                    "phone": parts[3].strip() if len(parts) > 3 else "",
                    "channel": conversation.channel,
                },
            )
        except Exception:
            pass


# ─────────────────────────────────────────────
# Dashboard — Conversation Management
# ─────────────────────────────────────────────

class ConversationListView(APIView):
    """
    GET /api/conversations/?bot=<bot_id>&channel=website&mode=ai&page=1
    List all conversations for the tenant with optional filters.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Conversation.objects.filter(
            bot__tenant=request.user.tenant
        ).select_related("assigned_agent").prefetch_related("messages")

        bot_id = request.query_params.get("bot")
        if bot_id:
            qs = qs.filter(bot_id=bot_id)

        channel = request.query_params.get("channel")
        if channel:
            qs = qs.filter(channel=channel)

        mode = request.query_params.get("mode")
        if mode:
            qs = qs.filter(mode=mode)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                models.Q(customer_name__icontains=search) |
                models.Q(customer_email__icontains=search) |
                models.Q(messages__content__icontains=search)
            ).distinct()

        return Response(ConversationSerializer(qs, many=True).data)


class ConversationDetailView(APIView):
    """
    GET /api/conversations/<pk>/
    Full conversation with all messages.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, tenant):
        try:
            return Conversation.objects.prefetch_related("messages").get(
                pk=pk, bot__tenant=tenant
            )
        except Conversation.DoesNotExist:
            return None

    def get(self, request, pk):
        conv = self.get_object(pk, request.user.tenant)
        if not conv:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ConversationDetailSerializer(conv).data)

    def delete(self, request, pk):
        conv = self.get_object(pk, request.user.tenant)
        if not conv:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HandoffView(APIView):
    """
    POST /api/conversations/<pk>/handoff/
    Agent takes over (action=takeover) or releases (action=release) a conversation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk, bot__tenant=request.user.tenant)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = HumanHandoffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        if action == "takeover":
            conv.mode = "human"
            conv.assigned_agent = request.user
            conv.save(update_fields=["mode", "assigned_agent"])
            return Response({"detail": "You are now handling this conversation.", "mode": "human"})

        elif action == "release":
            conv.mode = "ai"
            conv.assigned_agent = None
            conv.save(update_fields=["mode", "assigned_agent"])
            return Response({"detail": "Conversation returned to AI.", "mode": "ai"})


class AgentMessageView(APIView):
    """
    POST /api/conversations/<pk>/message/
    Agent sends a message during human handoff.
    Also pushes the message to the correct channel (WhatsApp / FB / IG / website WS).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk, bot__tenant=request.user.tenant)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        if conv.mode != "human":
            return Response(
                {"detail": "This conversation is not in human handoff mode."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AgentMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data["content"]

        msg = Message.objects.create(
            conversation=conv,
            role="agent",
            content=content,
        )
        Conversation.objects.filter(pk=conv.pk).update(last_message_at=timezone.now())

        # Send back through the right channel
        self._dispatch_to_channel(conv, content)

        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    def _dispatch_to_channel(self, conversation, content):
        """Routes the agent reply to the correct messaging platform."""
        try:
            if conversation.channel == "whatsapp":
                from apps.messaging.whatsapp import send_whatsapp_message
                config = conversation.bot.whatsapp_config
                send_whatsapp_message(
                    to=conversation.channel_user_id,
                    message=content,
                    phone_number_id=config.phone_number_id,
                    access_token=config.access_token,
                )
            elif conversation.channel == "facebook":
                from apps.messaging.facebook import send_facebook_message
                config = conversation.bot.facebook_config
                send_facebook_message(
                    recipient_id=conversation.channel_user_id,
                    message=content,
                    page_access_token=config.page_access_token,
                )
            elif conversation.channel == "instagram":
                from apps.messaging.instagram import send_instagram_message
                config = conversation.bot.instagram_config
                send_instagram_message(
                    recipient_id=conversation.channel_user_id,
                    message=content,
                    page_access_token=config.page_access_token,
                )
            # website channel — WebSocket push handled by Django Channels consumer
        except Exception:
            pass  # don't break the response if channel dispatch fails


# needed for Q search filter
from django.db import models
