import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

from utils.router_constants import refresh_period_in_minutes, warm_lock_ttl_seconds
from utils.cache_store import _redis_client, _has_client
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
        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Scheduler refresh job: {job['name']}")
        job["refresh"]()
    except Exception as exc:
        logging.exception("Scheduler refresh job failed for %s: %s", job["name"], exc)


def _try_acquire_warm_lock(job_name):
    """Attempt to acquire a distributed lock for warm_cache.

    Returns True if the lock was acquired, False if another process already holds it.
    """
    if not _has_client():
        return True  # no Redis; allow warm to proceed (single-instance fallback)

    lock_key = f"warm_lock:{job_name}"
    try:
        # SET NX EX: only set if key does not exist, with TTL
        result = _redis_client.set(lock_key, "1", nx=True, ex=warm_lock_ttl_seconds)
        return result is True or result == 1
    except Exception as exc:
        logging.warning("Failed to acquire warm lock for %s: %s. Allowing warm to proceed.", job_name, exc)
        return True


def _release_warm_lock(job_name):
    """Release the distributed warm lock (fire-and-forget)."""
    if not _has_client():
        return

    lock_key = f"warm_lock:{job_name}"
    try:
        _redis_client.delete(lock_key)
    except Exception:
        pass  # ignore cleanup failures


def router_refresh_job_scheduler(jobs):
    global _scheduler_started
    if _scheduler_started:
        logging.info("Scheduler already started in this process; skipping duplicate initialization.")
        return None

    interval_minutes = _load_scheduler_interval_minutes()
    scheduler = BackgroundScheduler()
    scheduler.start()
    _scheduler_started = True

    for job in jobs:
        # warm_cache() returns True if it refreshed (cache was empty or lock acquired),
        # False if it skipped (cache was populated or lock held by another process)
        cache_was_empty = None  # None = skipped for an external reason (lock held or error)
        lock_held_by_other = False
        try:
            if _try_acquire_warm_lock(job["name"]):
                try:
                    cache_was_empty = job["warmup"]()
                finally:
                    _release_warm_lock(job["name"])
            else:
                logging.info(
                    "%s Router %s: warm-up skipped; another process is refreshing.",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    job['name'],
                )
                lock_held_by_other = True
        except Exception as exc:
            logging.exception("Scheduler warm-up job failed for %s: %s", job['name'], exc)
            cache_was_empty = False

        if cache_was_empty is True:
            logging.info(
                "%s Router %s: cache was empty, warm-up refreshed content. Next scheduled run in %s minutes.",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                job['name'],
                interval_minutes,
            )
        elif lock_held_by_other:
            logging.info(
                "%s Router %s: warm-up deferred to another process. Next scheduled run in %s minutes.",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                job['name'],
                interval_minutes,
            )
        else:
            logging.info(
                "%s Router %s: cache was populated, skipping warm-up. Next scheduled run in %s minutes.",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
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
