import logging
import os

from flask import Flask


def create_app():
    from application.routes import register_routes

    flask_app = Flask(__name__)
    flask_app.logger.setLevel(logging.DEBUG)
    register_routes(flask_app)
    return flask_app


def should_start_scheduler():
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return True

    if os.environ.get("FLASK_DEBUG") == "1":
        logging.info("Skipping scheduler startup in Flask reloader parent process.")
        return False

    return True


def start_scheduler_if_needed():
    if should_start_scheduler():
        from application.scheduler_jobs import build_scheduler_jobs
        from utils.scheduler import router_refresh_job_scheduler

        router_refresh_job_scheduler(build_scheduler_jobs())
