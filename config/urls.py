from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth
    path("api/auth/", include("apps.accounts.urls")),

    # Bots
    path("api/bots/", include("apps.bots.urls")),

    # Knowledge Base
    path("api/knowledge/", include("apps.knowledge.urls")),

    # Chat (public — widget) + Conversations (dashboard)
    path("api/", include("apps.conversations.urls")),

    # Messaging (Meta webhooks + connect/disconnect)
    path("api/messaging/", include("apps.messaging.urls")),

    # Leads
    path("api/leads/", include("apps.leads.urls")),

    # Analytics
    path("api/analytics/", include("apps.analytics.urls")),

    # Billing
    path("api/billing/", include("apps.billing.urls")),

    # Widget JS file
    path("widget.js", include("apps.bots.widget_urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
