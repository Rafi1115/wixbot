from rest_framework import serializers
from .models import Lead


class LeadSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    channel_display = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id", "bot", "conversation",
            "channel", "channel_display",
            "name", "email", "phone", "notes",
            "status", "status_display",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "bot", "conversation", "channel", "created_at", "updated_at"]

    def get_channel_display(self, obj):
        return obj.channel.replace("_", " ").title() if obj.channel else ""


class LeadUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ["name", "email", "phone", "notes", "status"]
