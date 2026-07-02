import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = Celery("backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

from celery.schedules import crontab

@app.task(bind=True)
def debug_task(self):
    return {"task_id": self.request.id, "args": self.request.args}

app.conf.beat_schedule = {
    'dispatch-daily-summaries-every-5-mins': {
        'task': 'notifications.dispatch_daily_summaries',
        'schedule': crontab(minute='*/5'),
    },
}
