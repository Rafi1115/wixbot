from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bots.models import Bot
from .models import KnowledgeSource, QAPair, GoogleDriveConfig, OneDriveConfig
from .serializers import (
    AddWebsiteSerializer,
    ExternalFileSerializer,
    GoogleDriveConfigSerializer,
    KnowledgeSourceSerializer,
    OneDriveConfigSerializer,
    QAPairSerializer,
    UploadFileSerializer,
)
from .tasks import process_file_task, scrape_website_task, process_qa_task, sync_external_file_task


def get_bot_for_tenant(pk, tenant):
    try:
        return Bot.objects.get(pk=pk, tenant=tenant)
    except Bot.DoesNotExist:
        return None


# ─────────────────────────────────────────────
# Website Links
# ─────────────────────────────────────────────

class WebsiteListView(APIView):
    """
    GET  /api/knowledge/<bot_pk>/websites/       — list all website sources
    POST /api/knowledge/<bot_pk>/websites/       — add a new URL
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        sources = KnowledgeSource.objects.filter(bot=bot, source_type="website")
        return Response(KnowledgeSourceSerializer(sources, many=True).data)

    def post(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AddWebsiteSerializer(data=request.data, context={"bot": bot})
        serializer.is_valid(raise_exception=True)

        source = KnowledgeSource.objects.create(
            bot=bot,
            source_type="website",
            url=serializer.validated_data["url"],
            auto_rescrape=serializer.validated_data["auto_rescrape"],
            status="pending",
        )
        # fire celery task
        scrape_website_task.delay(str(source.id))
        return Response(KnowledgeSourceSerializer(source).data, status=status.HTTP_201_CREATED)


class WebsiteDetailView(APIView):
    """
    GET    /api/knowledge/<bot_pk>/websites/<pk>/           — detail
    PATCH  /api/knowledge/<bot_pk>/websites/<pk>/           — toggle auto_rescrape
    DELETE /api/knowledge/<bot_pk>/websites/<pk>/           — remove
    POST   /api/knowledge/<bot_pk>/websites/<pk>/rescrape/  — manually trigger rescrape
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, bot_pk, pk, tenant):
        try:
            return KnowledgeSource.objects.get(
                pk=pk, bot__pk=bot_pk, bot__tenant=tenant, source_type="website"
            )
        except KnowledgeSource.DoesNotExist:
            return None

    def get(self, request, bot_pk, pk):
        source = self.get_object(bot_pk, pk, request.user.tenant)
        if not source:
            return Response({"detail": "Source not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(KnowledgeSourceSerializer(source).data)

    def patch(self, request, bot_pk, pk):
        source = self.get_object(bot_pk, pk, request.user.tenant)
        if not source:
            return Response({"detail": "Source not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = KnowledgeSourceSerializer(source, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, bot_pk, pk):
        source = self.get_object(bot_pk, pk, request.user.tenant)
        if not source:
            return Response({"detail": "Source not found."}, status=status.HTTP_404_NOT_FOUND)
        source.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebsiteRescrapeView(APIView):
    """POST /api/knowledge/<bot_pk>/websites/<pk>/rescrape/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, bot_pk, pk):
        try:
            source = KnowledgeSource.objects.get(
                pk=pk, bot__pk=bot_pk, bot__tenant=request.user.tenant, source_type="website"
            )
        except KnowledgeSource.DoesNotExist:
            return Response({"detail": "Source not found."}, status=status.HTTP_404_NOT_FOUND)

        source.status = "pending"
        source.save(update_fields=["status"])
        scrape_website_task.delay(str(source.id))
        return Response({"detail": "Rescrape started."})


# ─────────────────────────────────────────────
# File Uploads
# ─────────────────────────────────────────────

class FileUploadView(APIView):
    """
    GET  /api/knowledge/<bot_pk>/files/   — list uploaded files
    POST /api/knowledge/<bot_pk>/files/   — upload a new file
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        sources = KnowledgeSource.objects.filter(
            bot=bot, source_type__in=["pdf", "docx", "txt", "xlsx"]
        )
        return Response(KnowledgeSourceSerializer(sources, many=True).data)

    def post(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = UploadFileSerializer(data=request.data, context={"bot": bot})
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()

        source = KnowledgeSource.objects.create(
            bot=bot,
            source_type=ext,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            status="pending",
        )
        process_file_task.delay(str(source.id))
        return Response(KnowledgeSourceSerializer(source).data, status=status.HTTP_201_CREATED)


class FileDetailView(APIView):
    """DELETE /api/knowledge/<bot_pk>/files/<pk>/"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, bot_pk, pk):
        try:
            source = KnowledgeSource.objects.get(
                pk=pk, bot__pk=bot_pk, bot__tenant=request.user.tenant,
                source_type__in=["pdf", "docx", "txt", "xlsx"]
            )
        except KnowledgeSource.DoesNotExist:
            return Response({"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND)
        if source.file:
            source.file.delete(save=False)
        source.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
# Q&A Pairs
# ─────────────────────────────────────────────

class QAPairListView(APIView):
    """
    GET  /api/knowledge/<bot_pk>/qa/
    POST /api/knowledge/<bot_pk>/qa/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        pairs = QAPair.objects.filter(bot=bot)
        return Response(QAPairSerializer(pairs, many=True).data)

    def post(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QAPairSerializer(data=request.data, context={"bot": bot})
        serializer.is_valid(raise_exception=True)

        # create knowledge source entry first
        source = KnowledgeSource.objects.create(
            bot=bot,
            source_type="qa",
            status="pending",
        )
        qa = serializer.save(bot=bot, knowledge_source=source)
        process_qa_task.delay(str(source.id), str(qa.id))
        return Response(QAPairSerializer(qa).data, status=status.HTTP_201_CREATED)


class QAPairDetailView(APIView):
    """
    PATCH  /api/knowledge/<bot_pk>/qa/<pk>/
    DELETE /api/knowledge/<bot_pk>/qa/<pk>/
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, bot_pk, pk, tenant):
        try:
            return QAPair.objects.get(pk=pk, bot__pk=bot_pk, bot__tenant=tenant)
        except QAPair.DoesNotExist:
            return None

    def patch(self, request, bot_pk, pk):
        qa = self.get_object(bot_pk, pk, request.user.tenant)
        if not qa:
            return Response({"detail": "Q&A not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QAPairSerializer(
            qa, data=request.data, partial=True,
            context={"bot": qa.bot}
        )
        serializer.is_valid(raise_exception=True)
        qa = serializer.save()
        # re-embed updated Q&A
        if qa.knowledge_source:
            process_qa_task.delay(str(qa.knowledge_source.id), str(qa.id))
        return Response(serializer.data)

    def delete(self, request, bot_pk, pk):
        qa = self.get_object(bot_pk, pk, request.user.tenant)
        if not qa:
            return Response({"detail": "Q&A not found."}, status=status.HTTP_404_NOT_FOUND)
        if qa.knowledge_source:
            qa.knowledge_source.delete()  # cascades to qa
        else:
            qa.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
# External Sources — Google Drive & OneDrive
# ─────────────────────────────────────────────

class GoogleDriveStatusView(APIView):
    """GET /api/knowledge/<bot_pk>/gdrive/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            config = GoogleDriveConfig.objects.get(bot=bot)
            return Response({"connected": True, **GoogleDriveConfigSerializer(config).data})
        except GoogleDriveConfig.DoesNotExist:
            return Response({"connected": False})

    def delete(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        GoogleDriveConfig.objects.filter(bot=bot).delete()
        return Response({"detail": "Google Drive disconnected."})


class OneDriveStatusView(APIView):
    """GET /api/knowledge/<bot_pk>/onedrive/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            config = OneDriveConfig.objects.get(bot=bot)
            return Response({"connected": True, **OneDriveConfigSerializer(config).data})
        except OneDriveConfig.DoesNotExist:
            return Response({"connected": False})

    def delete(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        OneDriveConfig.objects.filter(bot=bot).delete()
        return Response({"detail": "OneDrive disconnected."})


class ImportExternalFileView(APIView):
    """POST /api/knowledge/<bot_pk>/import-external/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, bot_pk):
        bot = get_bot_for_tenant(bot_pk, request.user.tenant)
        if not bot:
            return Response({"detail": "Bot not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ExternalFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        source = KnowledgeSource.objects.create(
            bot=bot,
            source_type=serializer.validated_data["source_type"],
            external_file_id=serializer.validated_data["file_id"],
            external_file_name=serializer.validated_data["file_name"],
            status="pending",
        )
        sync_external_file_task.delay(str(source.id))
        return Response(KnowledgeSourceSerializer(source).data, status=status.HTTP_201_CREATED)
