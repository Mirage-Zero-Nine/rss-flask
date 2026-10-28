"""One production WSGI process and one in-process refresh scheduler."""

from __future__ import annotations

import logging
import signal

from waitress.server import create_server


def _stop(_signum, _frame) -> None:
    raise KeyboardInterrupt


def main() -> None:
    from utils.logging_config import configure_logging

    configure_logging()
    # Import wiring only in the executable entry point, after logging is ready.
    from application.factory import create_app, start_scheduler_if_needed
    from utils.cache_store import cache_is_ready

    signal.signal(signal.SIGTERM, _stop)
    app = create_app()
    if not cache_is_ready():
        raise RuntimeError("Redis readiness failed; refusing an empty-cache server")

    scheduler = None
    server = None
    try:
        scheduler = start_scheduler_if_needed()
        server = create_server(
            app, listen="0.0.0.0:5000", threads=4, connection_limit=64,
            channel_timeout=120, max_request_header_size=32768,
            max_request_body_size=1048576, expose_tracebacks=False,
            clear_untrusted_proxy_headers=True,
        )
        logging.info("Production RSS server ready on port 5000 (one scheduler process)")
        server.run()
    except KeyboardInterrupt:
        logging.info("Stopping RSS server and refresh scheduler")
    finally:
        if server is not None:
            server.close()
            server.task_dispatcher.shutdown(timeout=30)
        if scheduler is not None:
            scheduler.shutdown(wait=True)


if __name__ == "__main__":
    main()
