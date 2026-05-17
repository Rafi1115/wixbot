from django.urls import path
from . import views

urlpatterns = [
    # public — widget
    path("chat/", views.ChatView.as_view()),
    # dashboard
    path("", views.ConversationListView.as_view()),
    path("<uuid:pk>/", views.ConversationDetailView.as_view()),
    path("<uuid:pk>/handoff/", views.HandoffView.as_view()),
    path("<uuid:pk>/message/", views.AgentMessageView.as_view()),
]
