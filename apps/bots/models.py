import uuid
from django.db import models
from apps.accounts.models import Tenant


class Bot(models.Model):
    """A chatbot configured by a tenant."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="bots")
    name = models.CharField(max_length=255)
    business_context = models.TextField(
        blank=True,
        help_text="Describe what your business does — the bot will use this as its persona.",
    )
    widget_enabled = models.BooleanField(default=True)
    # message usage tracking (reset monthly by billing task)
    messages_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"

    def is_within_message_limit(self) -> bool:
        """Check if bot has remaining messages this month."""
        limit = self.tenant.get_plan_limits()["messages"]
        return self.messages_used < limit

    def increment_messages(self):
        """Atomically increment message usage counter."""
        Bot.objects.filter(pk=self.pk).update(
            messages_used=models.F("messages_used") + 1
        )
        self.refresh_from_db(fields=["messages_used"])


class BotBehavior(models.Model):
    """Custom behaviour instruction for a bot (e.g. 'Always greet in Arabic')."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="behaviors")
    instruction = models.TextField(max_length=250)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.bot.name}: {self.instruction[:60]}"


class BotDesign(models.Model):
    """Visual / UX configuration for the embedded chat widget."""
    POSITION_CHOICES = [("left", "Left"), ("right", "Right")]
    SIZE_CHOICES = [("small", "Small"), ("medium", "Medium"), ("large", "Large")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.OneToOneField(Bot, on_delete=models.CASCADE, related_name="design")
    header_text = models.CharField(max_length=255, default="Chat with us")
    welcome_message = models.TextField(default="Hi! How can I help you today?")
    predefined_questions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of pre-filled questions shown in the widget.",
    )
    input_placeholder = models.CharField(max_length=255, default="Type a message...")
    theme_color = models.CharField(max_length=20, default="#5B21B6")
    font_family = models.CharField(max_length=100, default="Inter")
    widget_position = models.CharField(
        max_length=10, choices=POSITION_CHOICES, default="right"
    )
    widget_size = models.CharField(
        max_length=10, choices=SIZE_CHOICES, default="medium"
    )
    border_radius = models.PositiveIntegerField(default=12)
    header_logo = models.ImageField(
        upload_to="bots/logos/", blank=True, null=True
    )
    widget_icon = models.ImageField(
        upload_to="bots/icons/", blank=True, null=True
    )
    remove_branding = models.BooleanField(default=False)
    enable_pulsing = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Design for {self.bot.name}"
