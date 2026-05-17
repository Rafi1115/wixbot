from rest_framework import serializers
from .models import FacebookConfig, InstagramConfig, WhatsAppConfig


class FacebookConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacebookConfig
        fields = ["id", "page_id", "page_name", "is_active", "connected_at"]
        read_only_fields = ["id", "connected_at"]


class InstagramConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramConfig
        fields = ["id", "instagram_account_id", "username", "is_active", "connected_at"]
        read_only_fields = ["id", "connected_at"]


class WhatsAppConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppConfig
        fields = ["id", "phone_number_id", "phone_number", "is_active", "connected_at"]
        read_only_fields = ["id", "connected_at"]


class ConnectFacebookSerializer(serializers.Serializer):
    """Payload after FB OAuth completes — frontend sends us the tokens."""
    bot_id = serializers.UUIDField()
    page_id = serializers.CharField()
    page_name = serializers.CharField(required=False, allow_blank=True)
    page_access_token = serializers.CharField()


class ConnectInstagramSerializer(serializers.Serializer):
    bot_id = serializers.UUIDField()
    instagram_account_id = serializers.CharField()
    page_id = serializers.CharField(required=False, allow_blank=True)
    page_access_token = serializers.CharField()
    username = serializers.CharField(required=False, allow_blank=True)


class ConnectWhatsAppSerializer(serializers.Serializer):
    bot_id = serializers.UUIDField()
    phone_number_id = serializers.CharField()
    phone_number = serializers.CharField(required=False, allow_blank=True)
    business_account_id = serializers.CharField(required=False, allow_blank=True)
    access_token = serializers.CharField()
