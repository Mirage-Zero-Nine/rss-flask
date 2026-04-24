import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from pathlib import Path
import yaml

from utils.router_constants import refresh_period_in_minutes

_scheduler_started = False


def _load_scheduler_interval_minutes():
    config_data = {}
    config_path = Path(__file__).resolve().parents[1] / "config.yml"
    if not config_path.exists():
        fallback_path = Path.cwd() / "config.yml"
        if fallback_path != config_path and fallback_path.exists():
            config_path = fallback_path

    if config_path.exists():
        try:
            with open(config_path) as config_file:
                config_data = yaml.safe_load(config_file) or {}
        except yaml.YAMLError as exc:
            logging.warning("Failed to parse scheduler config from %s: %s", config_path, exc)

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


def run_warmup_jobs(jobs):
    for job in jobs:
        try:
            logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Scheduler warm-up job: {job['name']}")
            job["warmup"]()
        except Exception as exc:
            logging.exception("Scheduler warm-up job failed for %s: %s", job["name"], exc)


def router_refresh_job_scheduler(jobs):
    global _scheduler_started
    if _scheduler_started:
        logging.info("Scheduler already started in this process; skipping duplicate initialization.")
        return None

    interval_minutes = _load_scheduler_interval_minutes()
    scheduler = BackgroundScheduler()
    scheduler.start()
    _scheduler_started = True

    run_warmup_jobs(jobs)

    for job in jobs:
        logging.info(
            "%s Router %s added to scheduler job with interval_minutes=%s.",
            datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            job['name'],
            interval_minutes
        )
        scheduler.add_job(
            run_refresh_job,
            trigger='interval',
            minutes=interval_minutes,
            next_run_time=datetime.now() + timedelta(minutes=interval_minutes),
            args=[job]
        )
