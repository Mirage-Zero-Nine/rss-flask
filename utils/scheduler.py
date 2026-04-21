import logging

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from utils.log_context import log_with_context, router_log_context


def refresh_router_job(router, job_definition):
    with router_log_context(router.__class__.__name__, router.router_path, "scheduler-refresh"):
        try:
            log_with_context(
                logging.INFO,
                "scheduler_refresh_start job_id=%s router_key=%s interval_minutes=%s parameter=%s",
                job_definition.job_id,
                job_definition.router_key,
                job_definition.interval_minutes,
                job_definition.parameter,
            )
            router.refresh_cache(
                parameter=job_definition.parameter,
                link_filter=job_definition.link_filter,
                title_filter=job_definition.title_filter,
            )
        except Exception as exc:
            log_with_context(
                logging.ERROR,
                "scheduler_refresh_failed job_id=%s router_key=%s parameter=%s error=%s",
                job_definition.job_id,
                job_definition.router_key,
                job_definition.parameter,
                exc,
                exc_info=exc,
            )


def warmup_router_job(router, job_definition):
    with router_log_context(router.__class__.__name__, router.router_path, "scheduler-warmup"):
        try:
            has_cache = router.has_cached_feed(parameter=job_definition.parameter)
            if has_cache:
                log_with_context(
                    logging.INFO,
                    "scheduler_warmup_skip job_id=%s router_key=%s parameter=%s reason=cache-present",
                    job_definition.job_id,
                    job_definition.router_key,
                    job_definition.parameter,
                )
                return

            log_with_context(
                logging.INFO,
                "scheduler_warmup_start job_id=%s router_key=%s parameter=%s",
                job_definition.job_id,
                job_definition.router_key,
                job_definition.parameter,
            )
            router.refresh_cache(
                parameter=job_definition.parameter,
                link_filter=job_definition.link_filter,
                title_filter=job_definition.title_filter,
            )
        except Exception as exc:
            log_with_context(
                logging.ERROR,
                "scheduler_warmup_failed job_id=%s router_key=%s parameter=%s error=%s",
                job_definition.job_id,
                job_definition.router_key,
                job_definition.parameter,
                exc,
                exc_info=exc,
            )


def router_refresh_job_scheduler(router_registry, refresh_jobs):
    scheduler = BackgroundScheduler()
    scheduler.start()

    for job in refresh_jobs:
        router = router_registry[job.router_key]
        warmup_router_job(router, job)

    for job in refresh_jobs:
        router = router_registry[job.router_key]
        with router_log_context(router.__class__.__name__, router.router_path, "scheduler-register"):
            log_with_context(
                logging.INFO,
                "scheduler_job_added job_id=%s router=%s interval_minutes=%s",
                job.job_id,
                router.router_path,
                job.interval_minutes,
            )
            scheduler.add_job(
                refresh_router_job,
                trigger="interval",
                id=job.job_id,
                minutes=job.interval_minutes,
                next_run_time=datetime.now(),
                args=[router, job],
            )
