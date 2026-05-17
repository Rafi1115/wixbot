from django.urls import path
from . import views

urlpatterns = [
    # websites
    path("<uuid:bot_pk>/websites/", views.WebsiteListView.as_view()),
    path("<uuid:bot_pk>/websites/<uuid:pk>/", views.WebsiteDetailView.as_view()),
    path("<uuid:bot_pk>/websites/<uuid:pk>/rescrape/", views.WebsiteRescrapeView.as_view()),
    # file uploads
    path("<uuid:bot_pk>/files/", views.FileUploadView.as_view()),
    path("<uuid:bot_pk>/files/<uuid:pk>/", views.FileDetailView.as_view()),
    # q&a pairs
    path("<uuid:bot_pk>/qa/", views.QAPairListView.as_view()),
    path("<uuid:bot_pk>/qa/<uuid:pk>/", views.QAPairDetailView.as_view()),
    # google drive
    path("<uuid:bot_pk>/gdrive/", views.GoogleDriveStatusView.as_view()),
    # onedrive
    path("<uuid:bot_pk>/onedrive/", views.OneDriveStatusView.as_view()),
    # import from external source
    path("<uuid:bot_pk>/import-external/", views.ImportExternalFileView.as_view()),
]
