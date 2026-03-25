import logging

from flask import Flask

from utils.cache_store import ensure_cache_connection
from utils.router_constants import refresh_period_in_minutes
from utils.scheduler import router_refresh_job_scheduler

from .feed_registry import SCHEDULED_ROUTE_PATHS
from .logging_config import configure_logging
from .routes import register_routes


def create_app():
    configure_logging()
    ensure_cache_connection()

    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)

    register_routes(app)
    router_refresh_job_scheduler(
        app,
        router_paths=SCHEDULED_ROUTE_PATHS,
        refresh_period_minutes=refresh_period_in_minutes,
    )
    return app
