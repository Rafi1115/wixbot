import hashlib
import hmac
import json

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bots.models import Bot
from apps.conversations.models import Conversation, Message
from apps.knowledge.rag import get_ai_response
from .models import FacebookConfig, InstagramConfig, WhatsAppConfig
from .serializers import (
    ConnectFacebookSerializer,
    ConnectInstagramSerializer,
    ConnectWhatsAppSerializer,
    FacebookConfigSerializer,
    InstagramConfigSerializer,
    WhatsAppConfigSerializer,
)
from .facebook import send_facebook_message
from .instagram import send_instagram_message
from .whatsapp import send_whatsapp_message


# ─────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────

def get_or_create_conversation(bot, channel, channel_user_id):
    conv, _ = Conversation.objects.get_or_create(
        channel_user_id=channel_user_id,
        channel=channel,
        bot=bot,
        defaults={"session_id": f"{channel}_{channel_user_id}_{bot.id}"},
    )
    return conv


def process_incoming_message(bot, conversation, text):
    """Run RAG + return AI reply. Respects human handoff mode."""
    if conversation.mode == "human":
        return None  # agent handles it, no AI reply

    Message.objects.create(conversation=conversation, role="user", content=text)

    history = list(
        conversation.messages.order_by("-created_at")
            .values("role", "content")[:6]
    )
    history.reverse()
    history = [
        {"role": m["role"] if m["role"] != "agent" else "assistant", "content": m["content"]}
        for m in history
    ]

    behaviors = bot.behaviors.all().values_list("instruction", flat=True)
    behavior_text = "\n".join(f"- {b}" for b in behaviors)

    reply = get_ai_response(
        question=text,
        bot_id=str(bot.id),
        business_context=bot.business_context,
        behavior_instructions=behavior_text,
        chat_history=history,
    )

    Message.objects.create(conversation=conversation, role="assistant", content=reply)
    Conversation.objects.filter(pk=conversation.pk).update(last_message_at=timezone.now())
    bot.increment_messages()
    return reply


# ─────────────────────────────────────────────
# Facebook Webhook
# ─────────────────────────────────────────────

class FacebookWebhookView(APIView):
    """
    GET  /api/messaging/facebook/webhook/  — verification handshake
    POST /api/messaging/facebook/webhook/  — incoming messages
    """
    permission_classes = [AllowAny]

    def get(self, request):
        verify_token = settings.META_WEBHOOK_VERIFY_TOKEN
        if request.query_params.get("hub.verify_token") == verify_token:
            return Response(int(request.query_params.get("hub.challenge", 0)))
        return Response("Invalid verify token.", status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        try:
            data = request.data
            for entry in data.get("entry", []):
                page_id = entry.get("id")
                for messaging in entry.get("messaging", []):
                    sender_id = messaging["sender"]["id"]
                    text = messaging.get("message", {}).get("text", "")
                    if not text:
                        continue

                    try:
                        config = FacebookConfig.objects.select_related("bot__tenant").get(
                            page_id=page_id, is_active=True
                        )
                    except FacebookConfig.DoesNotExist:
                        continue

                    bot = config.bot
                    if not bot.is_within_message_limit():
                        continue

                    conv = get_or_create_conversation(bot, "facebook", sender_id)
                    reply = process_incoming_message(bot, conv, text)
                    if reply:
                        send_facebook_message(sender_id, reply, config.page_access_token)

        except Exception as e:
            # always return 200 to Meta or it will retry endlessly
            pass

        return Response({"status": "ok"})


# ─────────────────────────────────────────────
# Instagram Webhook
# ─────────────────────────────────────────────

class InstagramWebhookView(APIView):
    """
    GET  /api/messaging/instagram/webhook/
    POST /api/messaging/instagram/webhook/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        verify_token = settings.META_WEBHOOK_VERIFY_TOKEN
        if request.query_params.get("hub.verify_token") == verify_token:
            return Response(int(request.query_params.get("hub.challenge", 0)))
        return Response("Invalid verify token.", status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        try:
            data = request.data
            for entry in data.get("entry", []):
                for messaging in entry.get("messaging", []):
                    sender_id = messaging["sender"]["id"]
                    text = messaging.get("message", {}).get("text", "")
                    if not text:
                        continue

                    # Instagram uses page_id to link to config
                    page_id = entry.get("id")
                    try:
                        config = InstagramConfig.objects.select_related("bot").get(
                            page_id=page_id, is_active=True
                        )
                    except InstagramConfig.DoesNotExist:
                        continue

                    bot = config.bot
                    if not bot.is_within_message_limit():
                        continue

                    conv = get_or_create_conversation(bot, "instagram", sender_id)
                    reply = process_incoming_message(bot, conv, text)
                    if reply:
                        send_instagram_message(sender_id, reply, config.page_access_token)

        except Exception:
            pass

        return Response({"status": "ok"})


# ─────────────────────────────────────────────
# WhatsApp Webhook
# ─────────────────────────────────────────────

class WhatsAppWebhookView(APIView):
    """
    GET  /api/messaging/whatsapp/webhook/
    POST /api/messaging/whatsapp/webhook/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        verify_token = settings.META_WEBHOOK_VERIFY_TOKEN
        if request.query_params.get("hub.verify_token") == verify_token:
            return Response(int(request.query_params.get("hub.challenge", 0)))
        return Response("Invalid verify token.", status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        try:
            data = request.data
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    phone_number_id = value.get("metadata", {}).get("phone_number_id")
                    messages = value.get("messages", [])

                    if not messages or not phone_number_id:
                        continue

                    try:
                        config = WhatsAppConfig.objects.select_related("bot").get(
                            phone_number_id=phone_number_id, is_active=True
                        )
                    except WhatsAppConfig.DoesNotExist:
                        continue

                    for msg in messages:
                        sender = msg.get("from")
                        text = msg.get("text", {}).get("body", "")
                        if not text:
                            continue

                        bot = config.bot
                        if not bot.is_within_message_limit():
                            continue

                        conv = get_or_create_conversation(bot, "whatsapp", sender)
                        reply = process_incoming_message(bot, conv, text)
                        if reply:
                            send_whatsapp_message(
                                to=sender,
                                message=reply,
                                phone_number_id=config.phone_number_id,
                                access_token=config.access_token,
                            )

        except Exception:
            pass

        return Response({"status": "ok"})


# ─────────────────────────────────────────────
# Connect / Disconnect Channels (Dashboard)
# ─────────────────────────────────────────────

class FacebookConnectView(APIView):
    """
    GET    /api/messaging/facebook/          — connection status
    POST   /api/messaging/facebook/connect/  — save connection
    DELETE /api/messaging/facebook/          — disconnect
    """
    permission_classes = [IsAuthenticated]

    def get_bot(self, bot_id, tenant):
        try:
            return Bot.objects.get(pk=bot_id, tenant=tenant)
        except Bot.DoesNotExist:
            return None

    def get(self, request):
        bot_id = request.query_params.get("bot")
        bot = self.get_bot(bot_id, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            config = FacebookConfig.objects.get(bot=bot)
            return Response({"connected": True, **FacebookConfigSerializer(config).data})
        except FacebookConfig.DoesNotExist:
            return Response({"connected": False})

    def post(self, request):
        serializer = ConnectFacebookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bot = self.get_bot(serializer.validated_data["bot_id"], request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)

        config, _ = FacebookConfig.objects.update_or_create(
            bot=bot,
            defaults={
                "page_id": serializer.validated_data["page_id"],
                "page_name": serializer.validated_data.get("page_name", ""),
                "page_access_token": serializer.validated_data["page_access_token"],
                "is_active": True,
            },
        )
        return Response(FacebookConfigSerializer(config).data)

    def delete(self, request):
        bot_id = request.query_params.get("bot")
        bot = self.get_bot(bot_id, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        FacebookConfig.objects.filter(bot=bot).delete()
        return Response({"detail": "Facebook disconnected."})


class InstagramConnectView(APIView):
    """
    GET    /api/messaging/instagram/
    POST   /api/messaging/instagram/connect/
    DELETE /api/messaging/instagram/
    """
    permission_classes = [IsAuthenticated]

    def get_bot(self, bot_id, tenant):
        try:
            return Bot.objects.get(pk=bot_id, tenant=tenant)
        except Bot.DoesNotExist:
            return None

    def get(self, request):
        bot_id = request.query_params.get("bot")
        bot = self.get_bot(bot_id, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            config = InstagramConfig.objects.get(bot=bot)
            return Response({"connected": True, **InstagramConfigSerializer(config).data})
        except InstagramConfig.DoesNotExist:
            return Response({"connected": False})

    def post(self, request):
        serializer = ConnectInstagramSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bot = self.get_bot(serializer.validated_data["bot_id"], request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)

        config, _ = InstagramConfig.objects.update_or_create(
            bot=bot,
            defaults={
                "instagram_account_id": serializer.validated_data["instagram_account_id"],
                "page_id": serializer.validated_data.get("page_id", ""),
                "page_access_token": serializer.validated_data["page_access_token"],
                "username": serializer.validated_data.get("username", ""),
                "is_active": True,
            },
        )
        return Response(InstagramConfigSerializer(config).data)

    def delete(self, request):
        bot_id = request.query_params.get("bot")
        bot = self.get_bot(bot_id, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        InstagramConfig.objects.filter(bot=bot).delete()
        return Response({"detail": "Instagram disconnected."})


class WhatsAppConnectView(APIView):
    """
    GET    /api/messaging/whatsapp/
    POST   /api/messaging/whatsapp/connect/
    DELETE /api/messaging/whatsapp/
    """
    permission_classes = [IsAuthenticated]

    def get_bot(self, bot_id, tenant):
        try:
            return Bot.objects.get(pk=bot_id, tenant=tenant)
        except Bot.DoesNotExist:
            return None

    def get(self, request):
        bot_id = request.query_params.get("bot")
        bot = self.get_bot(bot_id, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            config = WhatsAppConfig.objects.get(bot=bot)
            return Response({"connected": True, **WhatsAppConfigSerializer(config).data})
        except WhatsAppConfig.DoesNotExist:
            return Response({"connected": False})

    def post(self, request):
        serializer = ConnectWhatsAppSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bot = self.get_bot(serializer.validated_data["bot_id"], request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)

        config, _ = WhatsAppConfig.objects.update_or_create(
            bot=bot,
            defaults={
                "phone_number_id": serializer.validated_data["phone_number_id"],
                "phone_number": serializer.validated_data.get("phone_number", ""),
                "business_account_id": serializer.validated_data.get("business_account_id", ""),
                "access_token": serializer.validated_data["access_token"],
                "is_active": True,
            },
        )
        return Response(WhatsAppConfigSerializer(config).data)

    def delete(self, request):
        bot_id = request.query_params.get("bot")
        bot = self.get_bot(bot_id, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        WhatsAppConfig.objects.filter(bot=bot).delete()
        return Response({"detail": "WhatsApp disconnected."})
