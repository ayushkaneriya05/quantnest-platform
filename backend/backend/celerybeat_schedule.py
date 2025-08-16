# backend/celerybeat_schedule.py
from celery.schedules import schedule

CELERY_BEAT_SCHEDULE = {
    "publish-delayed-ticks-every-second": {
        "task": "marketdata.tasks.publish_delayed_ticks",
        "schedule": 1.0,
    },
    "build-and-flush-1m-every-10s": {
        "task": "marketdata.tasks.build_and_flush_1m_for_active_symbols",
        "schedule": 10.0,
    },
    # Auto close (run once daily at market close - schedule with crontab if you prefer)
    "auto-close-intraday-positions": {
        "task": "marketdata.tasks.auto_close_intraday_positions",
        "schedule": 60.0 * 60 * 24,  # placeholder daily; set proper crontab
    },
}
