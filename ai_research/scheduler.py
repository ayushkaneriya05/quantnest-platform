# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from utils import LOG
from scraper import crawl_groww

sched = None

def start_scheduler(app=None):
    global sched
    if sched:
        return
    sched = BackgroundScheduler(timezone="UTC")

    sched.add_job(crawl_groww, "interval", minutes=30, id="crawl_gr")

    sched.start()
    LOG.info("Scheduler started with jobs: %s", sched.get_jobs())
