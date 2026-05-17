import uuid
from django.db import models
from apps.bots.models import Bot


class SourceType(models.TextChoices):
    WEBSITE = "website", "Website"
    PDF = "pdf", "PDF"
    DOCX = "docx", "Word Document"
    TXT = "txt", "Text File"
    XLSX = "xlsx", "Excel File"
    QA = "qa", "Q&A Pair"
    GDRIVE = "gdrive", "Google Drive"
    ONEDRIVE = "onedrive", "OneDrive"


class SourceStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class KnowledgeSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="knowledge_sources")
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    # for websites
    url = models.URLField(blank=True)
    # for file uploads
    file = models.FileField(upload_to="knowledge_files/", null=True, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    # for google drive / onedrive
    external_file_id = models.CharField(max_length=500, blank=True)
    external_file_name = models.CharField(max_length=500, blank=True)
    # status tracking
    status = models.CharField(max_length=20, choices=SourceStatus.choices, default=SourceStatus.PENDING)
    error_message = models.TextField(blank=True)
    chunks_count = models.PositiveIntegerField(default=0)
    raw_text_preview = models.TextField(blank=True, help_text="First 500 chars of scraped text for preview")
    # auto rescraping (websites only)
    auto_rescrape = models.BooleanField(default=False)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_source_type_display()} — {self.url or self.original_filename or self.external_file_name}"


class QAPair(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="qa_pairs")
    question = models.TextField()
    answer = models.TextField()
    # links to the knowledge source entry for consistency
    knowledge_source = models.OneToOneField(
        KnowledgeSource,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="qa_pair",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Q: {self.question[:60]}"


class GoogleDriveConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.OneToOneField(Bot, on_delete=models.CASCADE, related_name="gdrive_config")
    access_token = models.TextField()
    refresh_token = models.TextField()
    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Google Drive — {self.bot.name}"


class OneDriveConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.OneToOneField(Bot, on_delete=models.CASCADE, related_name="onedrive_config")
    access_token = models.TextField()
    refresh_token = models.TextField()
    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OneDrive — {self.bot.name}"
