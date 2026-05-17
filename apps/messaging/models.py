import uuid
from django.db import models
from apps.bots.models import Bot


class FacebookConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.OneToOneField(Bot, on_delete=models.CASCADE, related_name="facebook_config")
    page_id = models.CharField(max_length=255, unique=True)
    page_name = models.CharField(max_length=255, blank=True)
    page_access_token = models.TextField()
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Facebook — {self.page_name or self.page_id}"


class InstagramConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.OneToOneField(Bot, on_delete=models.CASCADE, related_name="instagram_config")
    instagram_account_id = models.CharField(max_length=255, unique=True)
    page_id = models.CharField(max_length=255, blank=True)  # linked FB page
    page_access_token = models.TextField()
    username = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Instagram — @{self.username or self.instagram_account_id}"


class WhatsAppConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.OneToOneField(Bot, on_delete=models.CASCADE, related_name="whatsapp_config")
    phone_number_id = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=50, blank=True)
    business_account_id = models.CharField(max_length=255, blank=True)
    access_token = models.TextField()
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"WhatsApp — {self.phone_number or self.phone_number_id}"
