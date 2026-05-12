import logging
import os

from apscheduler.executors.pool import ThreadPoolExecutor as APSchedulerExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

from utils.router_constants import refresh_period_in_minutes
from utils.cache_store import acquire_warm_lock, release_warm_lock
from utils.config import load_config

_scheduler_started = False


def _load_scheduler_interval_minutes():
    config_data = load_config()
    configured_value = os.environ.get("RSS_SCHEDULER_REFRESH_PERIOD_MINUTES") or config_data.get("scheduler_refresh_period_in_minutes")
    if configured_value is None:
        return refresh_period_in_minutes

    try:
        return int(configured_value)
    except (TypeError, ValueError):
        logging.warning("Invalid scheduler_refresh_period_in_minutes=%s. Falling back to %s minutes.", configured_value, refresh_period_in_minutes)
        return refresh_period_in_minutes


def run_refresh_job(job):
    try:
        logging.info("Scheduler refresh job: %s", job['name'])
        job["refresh"]()
    except Exception as exc:
        logging.exception("Scheduler refresh job failed for %s: %s", job["name"], exc)


def router_refresh_job_scheduler(jobs):
    global _scheduler_started
    if _scheduler_started:
        logging.info("Scheduler already started in this process; skipping duplicate initialization.")
        return None

    interval_minutes = _load_scheduler_interval_minutes()
    scheduler = BackgroundScheduler(
        executors={"default": APSchedulerExecutor(max_workers=16)}
    )
    scheduler.start()
    _scheduler_started = True

    for job in jobs:
        # warm_cache() returns True if it refreshed (cache was empty or lock acquired),
        # False if it skipped (cache was populated or lock held by another process)
        cache_was_empty = None  # None = skipped for an external reason (lock held or error)
        lock_held_by_other = False
        try:
            if acquire_warm_lock(job["name"]):
                try:
                    cache_was_empty = job["warmup"]()
                finally:
                    release_warm_lock(job["name"])
            else:
                logging.info(
                    "Router %s: warm-up skipped; another process is refreshing.",
                    job['name'],
                )
                lock_held_by_other = True
        except Exception as exc:
            logging.exception("Scheduler warm-up job failed for %s: %s", job['name'], exc)
            cache_was_empty = False

        if cache_was_empty is True:
            logging.info(
                "Router %s: cache was empty, warm-up refreshed content. Next scheduled run in %s minutes.",
                job['name'],
                interval_minutes,
            )
        elif lock_held_by_other:
            logging.info(
                "Router %s: warm-up deferred to another process. Next scheduled run in %s minutes.",
                job['name'],
                interval_minutes,
            )
        else:
            logging.info(
                "Router %s: cache was populated, skipping warm-up. Next scheduled run in %s minutes.",
                job['name'],
                interval_minutes,
            )

        scheduler.add_job(
            run_refresh_job,
            trigger='interval',
            minutes=interval_minutes,
            next_run_time=datetime.now() + timedelta(minutes=interval_minutes),
            args=[job]
        )
