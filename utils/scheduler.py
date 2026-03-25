import logging

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime


def call_router(app, router_path):
    with app.test_request_context(router_path):
        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Scheduler run with path: {router_path}")
        app.dispatch_request()


def router_refresh_job_scheduler(app, router_paths, refresh_period_minutes):
    scheduler = BackgroundScheduler()
    scheduler.start()

    for r in router_paths:
        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Router {r} added to scheduler job.")
        scheduler.add_job(
            call_router,
            trigger='interval',
            minutes=refresh_period_minutes,
            next_run_time=datetime.now(),
            args=[app, r]
        )

    return scheduler
