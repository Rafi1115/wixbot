## apps/bots/widget_urls.py
from django.urls import path
from . import widget_views

urlpatterns = [
    path("", widget_views.ServeWidgetView.as_view()),
]
