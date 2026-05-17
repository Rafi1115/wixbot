from rest_framework import serializers
from .models import Bot, BotBehavior, BotDesign


class BotDesignSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotDesign
        fields = [
            "id", "header_text", "welcome_message", "predefined_questions",
            "input_placeholder", "theme_color", "font_family",
            "widget_position", "widget_size", "border_radius",
            "header_logo", "widget_icon",
            "remove_branding", "enable_pulsing", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BotBehaviorSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotBehavior
        fields = ["id", "instruction", "order", "created_at"]
        read_only_fields = ["id", "created_at"]


class BotSerializer(serializers.ModelSerializer):
    design = BotDesignSerializer(read_only=True)
    behaviors = BotBehaviorSerializer(many=True, read_only=True)
    messages_limit = serializers.SerializerMethodField()

    class Meta:
        model = Bot
        fields = [
            "id", "name", "business_context", "widget_enabled",
            "messages_used", "messages_limit",
            "design", "behaviors",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "messages_used", "created_at", "updated_at"]

    def get_messages_limit(self, obj):
        return obj.tenant.get_plan_limits()["messages"]


class BotCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bot
        fields = ["name", "business_context", "widget_enabled"]

    def validate(self, data):
        request = self.context["request"]
        tenant = request.user.tenant
        limit = tenant.get_plan_limits()["bots"]
        current = Bot.objects.filter(tenant=tenant).count()
        if current >= limit:
            raise serializers.ValidationError(
                f"Your plan allows {limit} bot(s). Upgrade to create more."
            )
        return data
