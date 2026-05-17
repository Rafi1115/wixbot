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
    website_url = serializers.URLField(required=False, allow_blank=True, write_only=True)
    files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False, use_url=False),
        required=False,
        write_only=True
    )

    class Meta:
        model = Bot
        fields = [
            "id", "name", "business_context", "widget_enabled",
            "messages_used", "messages_limit",
            "design", "behaviors",
            "created_at", "updated_at",
            "website_url", "files"
        ]
        read_only_fields = ["id", "messages_used", "created_at", "updated_at"]

    def get_messages_limit(self, obj):
        return obj.tenant.get_plan_limits()["messages"]

    def validate(self, data):
        website_url = data.get("website_url")
        files = data.get("files", [])

        new_sources_count = 0
        if website_url:
            new_sources_count += 1
        if files:
            new_sources_count += len(files)

        if new_sources_count > 0:
            instance = self.instance
            if instance:
                tenant = instance.tenant
            else:
                request = self.context.get("request")
                tenant = request.user.tenant if request else None

            if tenant:
                from apps.knowledge.models import KnowledgeSource
                current_ks = KnowledgeSource.objects.filter(bot__tenant=tenant).count()
                ks_limit = tenant.get_plan_limits()["knowledge_sources"]
                
                if current_ks + new_sources_count > ks_limit:
                    raise serializers.ValidationError(
                        f"Your plan allows a maximum of {ks_limit} knowledge source(s). "
                        f"You currently have {current_ks} and are trying to add {new_sources_count}."
                    )

            from apps.knowledge.serializers import ALLOWED_EXTENSIONS
            for f in files:
                ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
                if ext not in ALLOWED_EXTENSIONS:
                    raise serializers.ValidationError(
                        f"Unsupported file type '{ext}' for file '{f.name}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                    )
                max_mb = 20
                if f.size > max_mb * 1024 * 1024:
                    raise serializers.ValidationError(
                        f"File '{f.name}' is too large. Max size is {max_mb}MB."
                    )

        return data

    def update(self, instance, validated_data):
        website_url = validated_data.pop("website_url", None)
        files = validated_data.pop("files", [])

        # Update bot
        instance = super().update(instance, validated_data)

        # Create website source if website_url is present
        if website_url:
            website_url = website_url.rstrip("/")
            from apps.knowledge.models import KnowledgeSource
            from apps.knowledge.tasks import scrape_website_task

            source = KnowledgeSource.objects.create(
                bot=instance,
                source_type="website",
                url=website_url,
                auto_rescrape=False,
                status="pending",
            )
            scrape_website_task.delay(str(source.id))

        # Create file sources if files are present
        if files:
            from apps.knowledge.models import KnowledgeSource
            from apps.knowledge.tasks import process_file_task

            for uploaded_file in files:
                ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
                source = KnowledgeSource.objects.create(
                    bot=instance,
                    source_type=ext,
                    file=uploaded_file,
                    original_filename=uploaded_file.name,
                    status="pending",
                )
                process_file_task.delay(str(source.id))

        return instance



class BotCreateSerializer(serializers.ModelSerializer):
    website_url = serializers.URLField(required=False, allow_blank=True, write_only=True)
    files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False, use_url=False),
        required=False,
        write_only=True
    )

    class Meta:
        model = Bot
        fields = ["name", "business_context", "widget_enabled", "website_url", "files"]

    def validate(self, data):
        request = self.context["request"]
        tenant = request.user.tenant
        
        # 1. Check bot limits
        limit = tenant.get_plan_limits()["bots"]
        current = Bot.objects.filter(tenant=tenant).count()
        if current >= limit:
            raise serializers.ValidationError(
                f"Your plan allows {limit} bot(s). Upgrade to create more."
            )

        # 2. Check knowledge sources limits
        website_url = data.get("website_url")
        files = data.get("files", [])

        new_sources_count = 0
        if website_url:
            new_sources_count += 1
        if files:
            new_sources_count += len(files)

        if new_sources_count > 0:
            ks_limit = tenant.get_plan_limits()["knowledge_sources"]
            if new_sources_count > ks_limit:
                raise serializers.ValidationError(
                    f"Your plan allows a maximum of {ks_limit} knowledge source(s). "
                    f"You are trying to add {new_sources_count} source(s)."
                )

            from apps.knowledge.serializers import ALLOWED_EXTENSIONS
            for f in files:
                ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
                if ext not in ALLOWED_EXTENSIONS:
                    raise serializers.ValidationError(
                        f"Unsupported file type '{ext}' for file '{f.name}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                    )
                max_mb = 20
                if f.size > max_mb * 1024 * 1024:
                    raise serializers.ValidationError(
                        f"File '{f.name}' is too large. Max size is {max_mb}MB."
                    )

        return data

    def create(self, validated_data):
        website_url = validated_data.pop("website_url", None)
        files = validated_data.pop("files", [])

        # Create bot
        bot = super().create(validated_data)

        # Create website source if website_url is present
        if website_url:
            website_url = website_url.rstrip("/")
            from apps.knowledge.models import KnowledgeSource
            from apps.knowledge.tasks import scrape_website_task

            source = KnowledgeSource.objects.create(
                bot=bot,
                source_type="website",
                url=website_url,
                auto_rescrape=False,
                status="pending",
            )
            scrape_website_task.delay(str(source.id))

        # Create file sources if files are present
        if files:
            from apps.knowledge.models import KnowledgeSource
            from apps.knowledge.tasks import process_file_task

            for uploaded_file in files:
                ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
                source = KnowledgeSource.objects.create(
                    bot=bot,
                    source_type=ext,
                    file=uploaded_file,
                    original_filename=uploaded_file.name,
                    status="pending",
                )
                process_file_task.delay(str(source.id))

        return bot

