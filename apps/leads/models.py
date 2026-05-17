# ─── models.py ──────────────────────────────────────────────────────────────
import uuid
from django.db import models
from apps.bots.models import Bot
from apps.conversations.models import Conversation


class LeadStatus(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    CONVERTED = "converted", "Converted"
    LOST = "lost", "Lost"


class Lead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="leads")
    conversation = models.ForeignKey(
        Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads"
    )
    channel = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True, help_text="What the customer was asking about")
    status = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name or self.email or self.phone} — {self.status}"
