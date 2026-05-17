from celery import shared_task
from django.utils import timezone


@shared_task(bind=True, max_retries=3)
def scrape_website_task(self, source_id):
    """Scrapes a website URL and stores embeddings in ChromaDB."""
    from .models import KnowledgeSource
    from .scraper import scrape_website
    from .rag import store_knowledge

    try:
        source = KnowledgeSource.objects.get(id=source_id)
        source.status = "processing"
        source.save(update_fields=["status"])

        text = scrape_website(source.url)
        if not text:
            raise ValueError("No text could be scraped from this URL.")

        source.raw_text_preview = text[:500]
        chunks = store_knowledge(text, str(source.bot.id), source_name=str(source.id))
        source.chunks_count = chunks
        source.status = "ready"
        source.last_scraped_at = timezone.now()
        source.save(update_fields=["status", "chunks_count", "raw_text_preview", "last_scraped_at"])

    except Exception as exc:
        source = KnowledgeSource.objects.filter(id=source_id).first()
        if source:
            source.status = "failed"
            source.error_message = str(exc)
            source.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_file_task(self, source_id):
    """Reads an uploaded file (PDF/DOCX/TXT/XLSX) and stores embeddings."""
    from .models import KnowledgeSource
    from .file_readers import read_file
    from .rag import store_knowledge

    try:
        source = KnowledgeSource.objects.get(id=source_id)
        source.status = "processing"
        source.save(update_fields=["status"])

        text = read_file(source.file.path, source.source_type)
        if not text:
            raise ValueError("Could not extract text from this file.")

        source.raw_text_preview = text[:500]
        chunks = store_knowledge(text, str(source.bot.id), source_name=str(source.id))
        source.chunks_count = chunks
        source.status = "ready"
        source.save(update_fields=["status", "chunks_count", "raw_text_preview"])

    except Exception as exc:
        source = KnowledgeSource.objects.filter(id=source_id).first()
        if source:
            source.status = "failed"
            source.error_message = str(exc)
            source.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_qa_task(self, source_id, qa_id):
    """Embeds a Q&A pair into ChromaDB."""
    from .models import KnowledgeSource, QAPair
    from .rag import store_knowledge

    try:
        source = KnowledgeSource.objects.get(id=source_id)
        qa = QAPair.objects.get(id=qa_id)
        source.status = "processing"
        source.save(update_fields=["status"])

        text = f"Question: {qa.question}\nAnswer: {qa.answer}"
        chunks = store_knowledge(text, str(source.bot.id), source_name=str(source.id))
        source.chunks_count = chunks
        source.status = "ready"
        source.save(update_fields=["status", "chunks_count"])

    except Exception as exc:
        source = KnowledgeSource.objects.filter(id=source_id).first()
        if source:
            source.status = "failed"
            source.error_message = str(exc)
            source.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_external_file_task(self, source_id):
    """Downloads a file from Google Drive or OneDrive and embeds it."""
    from .models import KnowledgeSource
    from .rag import store_knowledge
    from .gdrive import download_gdrive_file
    from .onedrive import download_onedrive_file
    from .file_readers import read_file_from_bytes

    try:
        source = KnowledgeSource.objects.get(id=source_id)
        source.status = "processing"
        source.save(update_fields=["status"])

        if source.source_type == "gdrive":
            content, mime = download_gdrive_file(source.bot, source.external_file_id)
        else:
            content, mime = download_onedrive_file(source.bot, source.external_file_id)

        text = read_file_from_bytes(content, mime)
        source.raw_text_preview = text[:500]
        chunks = store_knowledge(text, str(source.bot.id), source_name=str(source.id))
        source.chunks_count = chunks
        source.status = "ready"
        source.last_scraped_at = timezone.now()
        source.save(update_fields=["status", "chunks_count", "raw_text_preview", "last_scraped_at"])

    except Exception as exc:
        source = KnowledgeSource.objects.filter(id=source_id).first()
        if source:
            source.status = "failed"
            source.error_message = str(exc)
            source.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc, countdown=60)


@shared_task
def auto_rescrape_websites():
    """
    Celery beat periodic task.
    Runs daily — rescrapes any website source with auto_rescrape=True
    whose last_scraped_at is older than 24 hours (Boost plan) or 30 days (Smart plan).
    """
    from .models import KnowledgeSource
    from django.utils import timezone
    from datetime import timedelta

    daily_threshold = timezone.now() - timedelta(hours=24)
    monthly_threshold = timezone.now() - timedelta(days=30)

    # Ultimo plan — daily rescrape
    ultimo_sources = KnowledgeSource.objects.filter(
        source_type="website",
        auto_rescrape=True,
        bot__tenant__plan="ultimo",
        last_scraped_at__lt=daily_threshold,
    )
    for source in ultimo_sources:
        scrape_website_task.delay(str(source.id))

    # Boost plan — monthly rescrape
    boost_sources = KnowledgeSource.objects.filter(
        source_type="website",
        auto_rescrape=True,
        bot__tenant__plan="boost",
        last_scraped_at__lt=monthly_threshold,
    )
    for source in boost_sources:
        scrape_website_task.delay(str(source.id))
