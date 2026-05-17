import uuid
from django.db import models
from apps.accounts.models import Tenant


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CANCELED = "canceled", "Canceled"
    PAST_DUE = "past_due", "Past Due"
    TRIALING = "trialing", "Trialing"
    INCOMPLETE = "incomplete", "Incomplete"


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="subscription")
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    stripe_price_id = models.CharField(max_length=255)
    plan = models.CharField(max_length=20)  # smart / boost / ultimo
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.name} — {self.plan} ({self.status})"


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="invoices")
    stripe_invoice_id = models.CharField(max_length=255, unique=True)
    amount_paid = models.PositiveIntegerField(help_text="In cents")
    currency = models.CharField(max_length=10, default="usd")
    status = models.CharField(max_length=50)
    invoice_pdf = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tenant.name} — ${self.amount_paid / 100:.2f}"
