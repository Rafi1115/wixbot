import os
from django.conf import settings
from django.http import HttpResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Bot


class ServeWidgetView(APIView):
    """
    GET /widget.js
    Serves the chat widget JavaScript file.
    Store owners paste this into their website:
    <script src="https://yourdomain.com/widget.js" data-bot-id="BOT_UUID"></script>
    """
    permission_classes = [AllowAny]

    def get(self, request):
        widget_path = os.path.join(settings.BASE_DIR, "widget", "widget.js")
        if not os.path.exists(widget_path):
            raise Http404("Widget not found.")
        with open(widget_path, "r") as f:
            content = f.read()
        return HttpResponse(
            content,
            content_type="application/javascript",
            headers={"Cache-Control": "public, max-age=3600"},
        )


class PublicBotConfigView(APIView):
    """
    GET /api/bots/public/<bot_id>/config/
    Public endpoint — called by the widget JS to get design config.
    No auth required.
    """
    permission_classes = [AllowAny]

    def get(self, request, bot_id):
        try:
            bot = Bot.objects.select_related("design").get(
                id=bot_id, widget_enabled=True
            )
        except Bot.DoesNotExist:
            return Response({"detail": "Bot not found."}, status=404)

        design = getattr(bot, "design", None)
        return Response({
            "bot_id": str(bot.id),
            "header_text": design.header_text if design else "Chat with us",
            "welcome_message": design.welcome_message if design else "Hi! How can I help?",
            "predefined_questions": design.predefined_questions if design else [],
            "input_placeholder": design.input_placeholder if design else "Type a message...",
            "theme_color": design.theme_color if design else "#5B21B6",
            "widget_position": design.widget_position if design else "right",
            "remove_branding": design.remove_branding if design else False,
            "enable_pulsing": design.enable_pulsing if design else True,
        })
