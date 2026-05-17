from django.urls import path
from . import views

urlpatterns = [
    # webhooks — public, called by Meta
    path("facebook/webhook/", views.FacebookWebhookView.as_view()),
    path("instagram/webhook/", views.InstagramWebhookView.as_view()),
    path("whatsapp/webhook/", views.WhatsAppWebhookView.as_view()),
    # connect / disconnect — authenticated dashboard actions
    path("facebook/", views.FacebookConnectView.as_view()),
    path("instagram/", views.InstagramConnectView.as_view()),
    path("whatsapp/", views.WhatsAppConnectView.as_view()),
]
