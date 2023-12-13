import logging

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from utils.router_constants import routers_to_call, refresh_period_in_minutes


def call_router(app, router_path):
    with app.test_request_context(router_path):
        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Scheduler run with path: {router_path}")
        app.dispatch_request()


def router_refresh_job_scheduler(app):
    # Create a scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()

    for r in routers_to_call:
        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Router {r} added to scheduler job.")
        scheduler.add_job(
            call_router,
            trigger='interval',
            minutes=refresh_period_in_minutes,
            next_run_time=datetime.now(),
            args=[app, r]
        )
