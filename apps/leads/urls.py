## leads/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.LeadListView.as_view()),
    path("export/", views.LeadExportView.as_view()),
    path("<uuid:pk>/", views.LeadDetailView.as_view()),
]
