import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class ConversationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the live dashboard.
    Agents connect here to receive real-time conversation updates.

    URL: ws://domain/ws/conversations/<bot_id>/

    Events pushed to the dashboard:
      - new_message: a new message arrived in any conversation
      - new_conversation: a new chat started
      - handoff_requested: customer wants a human (based on keywords)
      - conversation_updated: mode/agent changed
    """

    async def connect(self):
        self.bot_id = self.scope["url_route"]["kwargs"]["bot_id"]
        self.group_name = f"bot_{self.bot_id}"

        # reject unauthenticated connections
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser):
            await self.close(code=4001)
            return

        # verify user has access to this bot
        has_access = await self._user_has_bot_access(user, self.bot_id)
        if not has_access:
            await self.close(code=4003)
            return

        # join the bot's channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connected",
            "message": f"Connected to bot {self.bot_id} live updates.",
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle messages from the dashboard (ping/keep-alive)."""
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except Exception:
            pass

    # ── Handlers for group messages (pushed from views/tasks) ──

    async def new_message(self, event):
        """A new message arrived in a conversation."""
        await self.send(text_data=json.dumps({
            "type": "new_message",
            "conversation_id": event["conversation_id"],
            "message": event["message"],
        }))

    async def new_conversation(self, event):
        """A new conversation started."""
        await self.send(text_data=json.dumps({
            "type": "new_conversation",
            "conversation": event["conversation"],
        }))

    async def conversation_updated(self, event):
        """Conversation mode or assignment changed."""
        await self.send(text_data=json.dumps({
            "type": "conversation_updated",
            "conversation_id": event["conversation_id"],
            "data": event["data"],
        }))

    @database_sync_to_async
    def _user_has_bot_access(self, user, bot_id):
        from apps.bots.models import Bot
        return Bot.objects.filter(
            id=bot_id, tenant=user.tenant
        ).exists()


# ─────────────────────────────────────────────
# Helper to push events from Django views
# ─────────────────────────────────────────────

def push_new_message(bot_id: str, conversation_id: str, message: dict):
    """
    Call this from ChatView / messaging webhooks to push
    new messages to connected dashboard agents in real time.

    Usage:
        push_new_message(str(bot.id), str(conv.id), {
            "role": "user",
            "content": "Hello!",
            "created_at": "2026-01-01T12:00:00Z"
        })
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    group_name = f"bot_{bot_id}"

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "new_message",
            "conversation_id": conversation_id,
            "message": message,
        },
    )


def push_new_conversation(bot_id: str, conversation: dict):
    """Push a new conversation event to the dashboard."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"bot_{bot_id}",
        {
            "type": "new_conversation",
            "conversation": conversation,
        },
    )


def push_conversation_updated(bot_id: str, conversation_id: str, data: dict):
    """Push a conversation update (handoff, assignment) to the dashboard."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"bot_{bot_id}",
        {
            "type": "conversation_updated",
            "conversation_id": conversation_id,
            "data": data,
        },
    )
