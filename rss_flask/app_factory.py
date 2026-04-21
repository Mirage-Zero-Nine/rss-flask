import logging

from flask import Flask

from rss_flask.feed_registry import build_router_registry, build_scheduled_refresh_definitions
from rss_flask.logging_config import configure_logging
from rss_flask.routes import register_routes
from utils.cache_store import ensure_cache_connection
from utils.scheduler import router_refresh_job_scheduler


def create_app(start_scheduler=True):
    configure_logging()
    ensure_cache_connection()
    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)

    router_registry = build_router_registry()
    register_routes(app, router_registry)

    if start_scheduler:
        router_refresh_job_scheduler(router_registry, build_scheduled_refresh_definitions())

    return app
