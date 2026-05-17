from django.urls import path
from . import views

urlpatterns = [
    path("", views.BotListView.as_view()),
    path("<uuid:pk>/", views.BotDetailView.as_view()),
    path("<uuid:pk>/design/", views.BotDesignView.as_view()),
    path("<uuid:pk>/behaviors/", views.BotBehaviorListView.as_view()),
    path("<uuid:pk>/behaviors/<uuid:behavior_pk>/", views.BotBehaviorDetailView.as_view()),
]

# public endpoint for widget — no auth
from .widget_views import PublicBotConfigView
urlpatterns += [
    path("public/<uuid:bot_id>/config/", PublicBotConfigView.as_view()),
]
