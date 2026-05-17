import uuid
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Bot, BotBehavior, BotDesign
from .serializers import (
    BotBehaviorSerializer,
    BotDesignSerializer,
    BotSerializer,
    BotCreateSerializer,
)


def get_bot(pk, tenant):
    try:
        return Bot.objects.get(pk=pk, tenant=tenant)
    except Bot.DoesNotExist:
        return None


# ─────────────────────────────────────────────
# Bot CRUD
# ─────────────────────────────────────────────

class BotListView(APIView):
    """
    GET  /api/bots/   — list tenant's bots
    POST /api/bots/   — create a new bot
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bots = Bot.objects.filter(tenant=request.user.tenant)
        return Response(BotSerializer(bots, many=True).data)

    def post(self, request):
        serializer = BotCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        bot = serializer.save(tenant=request.user.tenant)
        # auto-create design defaults
        BotDesign.objects.get_or_create(bot=bot)
        return Response(BotSerializer(bot).data, status=status.HTTP_201_CREATED)


class BotDetailView(APIView):
    """
    GET    /api/bots/<pk>/   — retrieve
    PATCH  /api/bots/<pk>/   — update name / context / widget_enabled
    DELETE /api/bots/<pk>/   — delete
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        bot = get_bot(pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BotSerializer(bot).data)

    def patch(self, request, pk):
        bot = get_bot(pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BotSerializer(bot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        bot = get_bot(pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        bot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
# Bot Design
# ─────────────────────────────────────────────

class BotDesignView(APIView):
    """
    GET   /api/bots/<pk>/design/   — get design settings
    PATCH /api/bots/<pk>/design/   — update design settings
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        bot = get_bot(pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        design, _ = BotDesign.objects.get_or_create(bot=bot)
        return Response(BotDesignSerializer(design).data)

    def patch(self, request, pk):
        bot = get_bot(pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        design, _ = BotDesign.objects.get_or_create(bot=bot)
        serializer = BotDesignSerializer(design, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ─────────────────────────────────────────────
# Bot Behaviors
# ─────────────────────────────────────────────

class BotBehaviorListView(APIView):
    """
    GET  /api/bots/<pk>/behaviors/   — list behaviors
    POST /api/bots/<pk>/behaviors/   — add a behavior
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        bot = get_bot(pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        behaviors = BotBehavior.objects.filter(bot=bot)
        return Response(BotBehaviorSerializer(behaviors, many=True).data)

    def post(self, request, pk):
        bot = get_bot(pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BotBehaviorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        behavior = serializer.save(bot=bot)
        return Response(BotBehaviorSerializer(behavior).data, status=status.HTTP_201_CREATED)


class BotBehaviorDetailView(APIView):
    """
    PATCH  /api/bots/<pk>/behaviors/<behavior_pk>/
    DELETE /api/bots/<pk>/behaviors/<behavior_pk>/
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, behavior_pk, tenant):
        try:
            return BotBehavior.objects.get(pk=behavior_pk, bot__pk=pk, bot__tenant=tenant)
        except BotBehavior.DoesNotExist:
            return None

    def patch(self, request, pk, behavior_pk):
        behavior = self.get_object(pk, behavior_pk, request.user.tenant)
        if not behavior:
            return Response({"detail": "Behavior not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BotBehaviorSerializer(behavior, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk, behavior_pk):
        behavior = self.get_object(pk, behavior_pk, request.user.tenant)
        if not behavior:
            return Response({"detail": "Behavior not found."}, status=status.HTTP_404_NOT_FOUND)
        behavior.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
