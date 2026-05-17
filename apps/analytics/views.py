from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bots.models import Bot
from apps.conversations.models import Conversation, Message
from apps.leads.models import Lead


def get_bot_for_tenant(bot_id, tenant):
    try:
        return Bot.objects.get(pk=bot_id, tenant=tenant)
    except Bot.DoesNotExist:
        return None


def parse_date_range(request):
    """Extract start/end from query params, default to last 14 days."""
    end = timezone.now()
    start_str = request.query_params.get("start")
    end_str = request.query_params.get("end")
    try:
        from django.utils.dateparse import parse_datetime
        if start_str:
            start = parse_datetime(start_str) or (end - timedelta(days=14))
        else:
            start = end - timedelta(days=14)
        if end_str:
            end = parse_datetime(end_str) or end
    except Exception:
        start = end - timedelta(days=14)
    return start, end


class InsightsView(APIView):
    """
    GET /api/analytics/insights/?bot=<id>&start=2026-01-01&end=2026-01-31
    Returns: total chats, messages/chat, total messages, avg response time, messages used vs limit
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bot_id = request.query_params.get("bot")
        start, end = parse_date_range(request)

        convs = Conversation.objects.filter(bot__tenant=request.user.tenant)
        if bot_id:
            convs = convs.filter(bot_id=bot_id)
        convs = convs.filter(created_at__range=(start, end))

        total_chats = convs.count()
        total_messages = Message.objects.filter(
            conversation__in=convs
        ).count()
        avg_messages_per_chat = round(total_messages / total_chats, 1) if total_chats else 0
        avg_response_time = Message.objects.filter(
            conversation__in=convs,
            role="assistant",
            response_time_seconds__isnull=False,
        ).aggregate(avg=Avg("response_time_seconds"))["avg"] or 0

        # messages used this month vs plan limit
        if bot_id:
            bot = get_bot_for_tenant(bot_id, request.user.tenant)
            messages_used = bot.messages_used if bot else 0
            messages_limit = bot.tenant.get_plan_limits()["messages"] if bot else 0
        else:
            bots = Bot.objects.filter(tenant=request.user.tenant)
            messages_used = sum(b.messages_used for b in bots)
            messages_limit = request.user.tenant.get_plan_limits()["messages"]

        return Response({
            "total_chats": total_chats,
            "total_messages": total_messages,
            "avg_messages_per_chat": avg_messages_per_chat,
            "avg_response_time_seconds": round(avg_response_time, 1),
            "messages_used": messages_used,
            "messages_limit": messages_limit,
            "date_range": {"start": start, "end": end},
        })


class UserLocationsView(APIView):
    """
    GET /api/analytics/locations/?bot=<id>
    Returns customer country breakdown.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bot_id = request.query_params.get("bot")
        qs = Conversation.objects.filter(
            bot__tenant=request.user.tenant
        ).exclude(customer_country="")

        if bot_id:
            qs = qs.filter(bot_id=bot_id)

        locations = (
            qs.values("customer_country")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response(list(locations))


class TopQuestionsView(APIView):
    """
    GET /api/analytics/top-questions/?bot=<id>&limit=10
    Most common user messages — simple frequency analysis.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bot_id = request.query_params.get("bot")
        limit = int(request.query_params.get("limit", 10))

        msgs = Message.objects.filter(
            role="user",
            conversation__bot__tenant=request.user.tenant,
        )
        if bot_id:
            msgs = msgs.filter(conversation__bot_id=bot_id)

        top = (
            msgs.values("content")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )
        return Response(list(top))


class ChatsOverTimeView(APIView):
    """
    GET /api/analytics/chats-over-time/?bot=<id>&start=&end=
    Daily conversation and message counts for charting.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models.functions import TruncDate

        bot_id = request.query_params.get("bot")
        start, end = parse_date_range(request)

        convs = Conversation.objects.filter(
            bot__tenant=request.user.tenant,
            created_at__range=(start, end),
        )
        if bot_id:
            convs = convs.filter(bot_id=bot_id)

        daily = (
            convs.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(chats=Count("id"))
            .order_by("date")
        )

        msgs = Message.objects.filter(
            conversation__bot__tenant=request.user.tenant,
            created_at__range=(start, end),
        )
        if bot_id:
            msgs = msgs.filter(conversation__bot_id=bot_id)

        daily_msgs = (
            msgs.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(messages=Count("id"))
            .order_by("date")
        )

        return Response({
            "chats_per_day": list(daily),
            "messages_per_day": list(daily_msgs),
        })


class LeadsSummaryView(APIView):
    """GET /api/analytics/leads/?bot=<id>"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bot_id = request.query_params.get("bot")
        qs = Lead.objects.filter(bot__tenant=request.user.tenant)
        if bot_id:
            qs = qs.filter(bot_id=bot_id)

        summary = qs.values("status").annotate(count=Count("id"))
        by_channel = qs.values("channel").annotate(count=Count("id"))

        return Response({
            "total": qs.count(),
            "by_status": list(summary),
            "by_channel": list(by_channel),
        })
