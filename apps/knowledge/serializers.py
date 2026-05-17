from rest_framework import serializers
from .models import GoogleDriveConfig, KnowledgeSource, OneDriveConfig, QAPair

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "xlsx", "doc"}


class KnowledgeSourceSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)

    class Meta:
        model = KnowledgeSource
        fields = [
            "id", "source_type", "source_type_display", "url",
            "original_filename", "external_file_name",
            "status", "error_message", "chunks_count",
            "raw_text_preview", "auto_rescrape",
            "last_scraped_at", "created_at",
        ]
        read_only_fields = [
            "id", "source_type", "status", "error_message",
            "chunks_count", "raw_text_preview",
            "last_scraped_at", "created_at",
        ]


class AddWebsiteSerializer(serializers.Serializer):
    url = serializers.URLField()
    auto_rescrape = serializers.BooleanField(default=False)

    def validate_url(self, value):
        # strip trailing slash for consistency
        return value.rstrip("/")

    def validate(self, data):
        bot = self.context["bot"]
        # check plan limit on knowledge sources
        limit = bot.tenant.get_plan_limits()["knowledge_sources"]
        current = KnowledgeSource.objects.filter(bot=bot).count()
        if current >= limit:
            raise serializers.ValidationError(
                f"Your plan allows {limit} knowledge sources. Upgrade to add more."
            )
        # no duplicate URLs per bot
        if KnowledgeSource.objects.filter(bot=bot, url=data["url"]).exists():
            raise serializers.ValidationError("This URL is already in your knowledge base.")
        return data


class UploadFileSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        ext = value.name.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        max_mb = 20
        if value.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"File too large. Max size is {max_mb}MB.")
        return value

    def validate(self, data):
        bot = self.context["bot"]
        limit = bot.tenant.get_plan_limits()["knowledge_sources"]
        current = KnowledgeSource.objects.filter(bot=bot).count()
        if current >= limit:
            raise serializers.ValidationError(
                f"Your plan allows {limit} knowledge sources. Upgrade to add more."
            )
        return data


class QAPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = QAPair
        fields = ["id", "question", "answer", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        bot = self.context["bot"]
        limit = bot.tenant.get_plan_limits()["knowledge_sources"]
        current = KnowledgeSource.objects.filter(bot=bot).count()
        if not self.instance and current >= limit:
            raise serializers.ValidationError(
                f"Your plan allows {limit} knowledge sources. Upgrade to add more."
            )
        return data


class GoogleDriveConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleDriveConfig
        fields = ["id", "connected_at"]
        read_only_fields = ["id", "connected_at"]


class OneDriveConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneDriveConfig
        fields = ["id", "connected_at"]
        read_only_fields = ["id", "connected_at"]


class ExternalFileSerializer(serializers.Serializer):
    """Used when importing a file from Google Drive or OneDrive"""
    file_id = serializers.CharField()
    file_name = serializers.CharField()
    source_type = serializers.ChoiceField(choices=["gdrive", "onedrive"])
