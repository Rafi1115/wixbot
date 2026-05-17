from django.urls import path
from . import views

urlpatterns = [
    path("insights/", views.InsightsView.as_view()),
    path("locations/", views.UserLocationsView.as_view()),
    path("top-questions/", views.TopQuestionsView.as_view()),
    path("chats-over-time/", views.ChatsOverTimeView.as_view()),
    path("leads/", views.LeadsSummaryView.as_view()),
]
