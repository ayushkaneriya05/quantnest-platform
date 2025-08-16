# Add or merge into your celery settings area, e.g., backend/backend/celery.py or backend/settings.py
from celery.schedules import schedule

CELERY_BEAT_SCHEDULE = {
    # publish delayed ticks every second
    "publish-delayed-ticks-every-second": {
        "task": "marketdata.tasks.publish_delayed_ticks",
        "schedule": 1.0,  # seconds
    },
    # run 1m builder for active symbols every 10 seconds
    "build-and-flush-1m-every-10s": {
        "task": "marketdata.tasks.build_and_flush_1m_for_active_symbols",
        "schedule": 10.0,
    },
}
