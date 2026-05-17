import uuid
from django.db import models
from apps.bots.models import Bot
from apps.accounts.models import User


class Channel(models.TextChoices):
    WEBSITE = "website", "Website"
    WHATSAPP = "whatsapp", "WhatsApp"
    FACEBOOK = "facebook", "Facebook Messenger"
    INSTAGRAM = "instagram", "Instagram DM"


class ConversationMode(models.TextChoices):
    AI = "ai", "AI"
    HUMAN = "human", "Human Handoff"


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="conversations")
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.WEBSITE)
    mode = models.CharField(max_length=10, choices=ConversationMode.choices, default=ConversationMode.AI)
    assigned_agent = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_conversations"
    )
    # customer identity — filled as we learn from the conversation
    customer_name = models.CharField(max_length=255, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=50, blank=True)
    # channel-specific identifiers (WhatsApp number, FB PSID, IG user id)
    channel_user_id = models.CharField(max_length=255, blank=True, db_index=True)
    # geo
    customer_country = models.CharField(max_length=100, blank=True)
    customer_ip = models.GenericIPAddressField(null=True, blank=True)
    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_message_at"]

    def __str__(self):
        return f"{self.channel} — {self.session_id[:8]}"


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    AGENT = "agent", "Human Agent"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=MessageRole.choices)
    content = models.TextField()
    # response time in seconds (for analytics)
    response_time_seconds = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"
