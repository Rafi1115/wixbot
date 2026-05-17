from rest_framework import serializers
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "response_time_seconds", "created_at"]
        read_only_fields = ["id", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    mode_display = serializers.CharField(source="get_mode_display", read_only=True)
    assigned_agent_name = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id", "session_id", "channel", "channel_display",
            "mode", "mode_display",
            "assigned_agent", "assigned_agent_name",
            "customer_name", "customer_email", "customer_phone",
            "customer_country",
            "last_message", "message_count",
            "created_at", "last_message_at",
        ]
        read_only_fields = ["id", "session_id", "channel", "created_at", "last_message_at"]

    def get_last_message(self, obj):
        last = obj.messages.last()
        if last:
            return {"role": last.role, "content": last.content[:100], "created_at": last.created_at}
        return None

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_assigned_agent_name(self, obj):
        if obj.assigned_agent:
            return obj.assigned_agent.full_name or obj.assigned_agent.email
        return None


class ConversationDetailSerializer(ConversationSerializer):
    """Full conversation with all messages — used when opening a chat."""
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]


class ChatRequestSerializer(serializers.Serializer):
    """Incoming message from the JS widget."""
    bot_id = serializers.UUIDField()
    session_id = serializers.CharField(max_length=255)
    message = serializers.CharField(max_length=2000)
    # optional customer info passed from widget
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)


class HumanHandoffSerializer(serializers.Serializer):
    """Agent takes over or releases a conversation."""
    action = serializers.ChoiceField(choices=["takeover", "release"])


class AgentMessageSerializer(serializers.Serializer):
    """Agent sends a message in human handoff mode."""
    content = serializers.CharField(max_length=2000)
