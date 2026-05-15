import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Week management
    'close-week-saturday-midnight': {
        'task': 'checkin.close_week_on_saturday',
        'schedule': crontab(hour=0, minute=0, day_of_week='sunday'),
    },
    'create-weekly-checkins-sunday': {
        'task': 'checkin.create_weekly_checkins_for_all_users',
        'schedule': crontab(hour=0, minute=1, day_of_week='sunday'),
    },
    # Weekly reminders
    'weekly-reminder-sunday': {
        'task': 'checkin.send_weekly_checkin_reminder',
        'schedule': crontab(hour=18, minute=0, day_of_week='sunday'),
    },
    'weekly-reminder-wednesday': {
        'task': 'checkin.send_weekly_checkin_reminder',
        'schedule': crontab(hour=19, minute=0, day_of_week='wednesday'),
    },
    'weekly-reminder-saturday': {
        'task': 'checkin.send_weekly_checkin_reminder',
        'schedule': crontab(hour=10, minute=0, day_of_week='saturday'),
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')