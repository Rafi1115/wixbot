"""
Billing periodic tasks.
"""
from celery import shared_task


@shared_task
def reset_message_counts():
    """
    Celery beat task — runs daily.
    Resets the messages_used counter for all bots whose billing period has renewed.
    For simplicity, this resets all bots on the 1st of every month.
    """
    from django.utils import timezone
    from apps.bots.models import Bot

    today = timezone.now().date()
    if today.day == 1:
        reset_count = Bot.objects.update(messages_used=0)
        return f"Reset message counts for {reset_count} bot(s)."
    return "Not billing cycle reset day — skipping."
