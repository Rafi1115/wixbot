from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import Tenant
from apps.bots.models import Bot
from apps.knowledge.models import KnowledgeSource

User = get_user_model()


class BotCreationTests(APITestCase):
    def setUp(self):
        # Create user and tenant
        self.tenant = Tenant.objects.create(name="Test Tenant")
        self.user = User.objects.create_user(
            email="testuser@test.com",
            password="Password123!",
            tenant=self.tenant,
            role=User.ROLE_OWNER,
            is_active=True
        )
        # Authenticate user
        self.client.force_authenticate(user=self.user)

    @patch("apps.knowledge.tasks.scrape_website_task.delay")
    @patch("apps.knowledge.tasks.process_file_task.delay")
    def test_create_bot_minimal(self, mock_process_file, mock_scrape_website):
        """Verify standard bot creation with only name works successfully."""
        data = {
            "name": "Minimal Bot",
            "business_context": "Minimal context",
            "widget_enabled": True
        }
        response = self.client.post("/api/bots/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bot.objects.filter(tenant=self.tenant).count(), 1)
        
        bot = Bot.objects.get(name="Minimal Bot")
        self.assertEqual(bot.business_context, "Minimal context")
        self.assertTrue(bot.widget_enabled)
        
        # Verify no Celery tasks were delayed
        mock_scrape_website.assert_not_called()
        mock_process_file.assert_not_called()

    @patch("apps.knowledge.tasks.scrape_website_task.delay")
    @patch("apps.knowledge.tasks.process_file_task.delay")
    def test_create_bot_with_website(self, mock_process_file, mock_scrape_website):
        """Verify bot creation with a website URL successfully creates the website source and triggers Celery."""
        data = {
            "name": "Website Bot",
            "website_url": "https://example.com"
        }
        response = self.client.post("/api/bots/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        bot = Bot.objects.get(name="Website Bot")
        # Check website source creation
        sources = KnowledgeSource.objects.filter(bot=bot)
        self.assertEqual(sources.count(), 1)
        
        source = sources.first()
        self.assertEqual(source.source_type, "website")
        self.assertEqual(source.url, "https://example.com")
        self.assertEqual(source.status, "pending")
        
        # Verify Celery scrape task was called
        mock_scrape_website.assert_called_once_with(str(source.id))
        mock_process_file.assert_not_called()

    @patch("apps.knowledge.tasks.scrape_website_task.delay")
    @patch("apps.knowledge.tasks.process_file_task.delay")
    def test_create_bot_with_files(self, mock_process_file, mock_scrape_website):
        """Verify bot creation with uploaded files successfully creates file sources and triggers Celery."""
        # Create dummy uploaded files
        file1 = SimpleUploadedFile("document1.pdf", b"pdf content", content_type="application/pdf")
        file2 = SimpleUploadedFile("document2.txt", b"txt content", content_type="text/plain")
        
        data = {
            "name": "Files Bot",
            "files": [file1, file2]
        }
        # Must use multipart format to upload files
        response = self.client.post("/api/bots/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        bot = Bot.objects.get(name="Files Bot")
        # Check file sources creation
        sources = KnowledgeSource.objects.filter(bot=bot).order_by("created_at")
        self.assertEqual(sources.count(), 2)
        
        source_txt = sources.filter(source_type="txt").first()
        source_pdf = sources.filter(source_type="pdf").first()
        
        self.assertIsNotNone(source_txt)
        self.assertEqual(source_txt.original_filename, "document2.txt")
        self.assertEqual(source_txt.status, "pending")
        
        self.assertIsNotNone(source_pdf)
        self.assertEqual(source_pdf.original_filename, "document1.pdf")
        self.assertEqual(source_pdf.status, "pending")
        
        # Verify Celery tasks were scheduled
        self.assertEqual(mock_process_file.call_count, 2)
        mock_scrape_website.assert_not_called()

    @patch("apps.knowledge.tasks.scrape_website_task.delay")
    @patch("apps.knowledge.tasks.process_file_task.delay")
    def test_create_bot_exceeding_plan_limits(self, mock_process_file, mock_scrape_website):
        """Verify validation fails when attempting to add more knowledge sources than allowed by the plan."""
        # Fetch actual plan limits for the test tenant
        limits = self.tenant.get_plan_limits()
        ks_limit = limits["knowledge_sources"]
        
        # We try to add ks_limit + 1 sources
        file_list = []
        for i in range(ks_limit + 1):
            file_list.append(SimpleUploadedFile(f"doc_{i}.txt", b"content", content_type="text/plain"))
            
        data = {
            "name": "Overlimit Bot",
            "files": file_list
        }
        
        response = self.client.post("/api/bots/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn("Your plan allows a maximum of", response.data["non_field_errors"][0])

    def test_create_bot_invalid_file_extension(self):
        """Verify file extension validation works correctly and rejects invalid extensions."""
        invalid_file = SimpleUploadedFile("unsafe.exe", b"malicious", content_type="application/octet-stream")
        
        data = {
            "name": "Invalid File Bot",
            "files": [invalid_file]
        }
        
        response = self.client.post("/api/bots/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn("Unsupported file type", response.data["non_field_errors"][0])

    @patch("apps.knowledge.tasks.scrape_website_task.delay")
    @patch("apps.knowledge.tasks.process_file_task.delay")
    def test_update_bot_minimal(self, mock_process_file, mock_scrape_website):
        """Verify updating a bot's standard fields works successfully."""
        bot = Bot.objects.create(name="Original Bot", tenant=self.tenant)
        data = {
            "name": "Updated Bot Name",
            "business_context": "Updated business context"
        }
        response = self.client.patch(f"/api/bots/{bot.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        bot.refresh_from_db()
        self.assertEqual(bot.name, "Updated Bot Name")
        self.assertEqual(bot.business_context, "Updated business context")
        mock_scrape_website.assert_not_called()
        mock_process_file.assert_not_called()

    @patch("apps.knowledge.tasks.scrape_website_task.delay")
    @patch("apps.knowledge.tasks.process_file_task.delay")
    def test_update_bot_with_website(self, mock_process_file, mock_scrape_website):
        """Verify updating a bot with a website URL successfully creates the website source and triggers Celery."""
        bot = Bot.objects.create(name="Original Bot", tenant=self.tenant)
        data = {
            "website_url": "https://newsite.com"
        }
        response = self.client.patch(f"/api/bots/{bot.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        sources = KnowledgeSource.objects.filter(bot=bot)
        self.assertEqual(sources.count(), 1)
        source = sources.first()
        self.assertEqual(source.source_type, "website")
        self.assertEqual(source.url, "https://newsite.com")
        
        mock_scrape_website.assert_called_once_with(str(source.id))
        mock_process_file.assert_not_called()

    @patch("apps.knowledge.tasks.scrape_website_task.delay")
    @patch("apps.knowledge.tasks.process_file_task.delay")
    def test_update_bot_with_files(self, mock_process_file, mock_scrape_website):
        """Verify updating a bot with uploaded files successfully creates file sources and triggers Celery."""
        bot = Bot.objects.create(name="Original Bot", tenant=self.tenant)
        file1 = SimpleUploadedFile("doc1.pdf", b"pdf content", content_type="application/pdf")
        
        data = {
            "files": [file1]
        }
        response = self.client.patch(f"/api/bots/{bot.id}/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        sources = KnowledgeSource.objects.filter(bot=bot)
        self.assertEqual(sources.count(), 1)
        source = sources.first()
        self.assertEqual(source.source_type, "pdf")
        self.assertEqual(source.original_filename, "doc1.pdf")
        
        mock_process_file.assert_called_once_with(str(source.id))
        mock_scrape_website.assert_not_called()

    def test_update_bot_exceeding_plan_limits(self):
        """Verify validation fails when attempting to update/add more knowledge sources than allowed by the plan."""
        bot = Bot.objects.create(name="Original Bot", tenant=self.tenant)
        limits = self.tenant.get_plan_limits()
        ks_limit = limits["knowledge_sources"]
        
        # We pre-create some knowledge sources to reach the limit
        for i in range(ks_limit):
            KnowledgeSource.objects.create(
                bot=bot,
                source_type="website",
                url=f"https://site-{i}.com",
                status="completed"
            )
            
        # Try to add another source
        data = {
            "website_url": "https://onemore.com"
        }
        response = self.client.patch(f"/api/bots/{bot.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn("Your plan allows a maximum of", response.data["non_field_errors"][0])

