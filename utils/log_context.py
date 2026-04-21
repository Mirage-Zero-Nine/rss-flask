import logging
from contextlib import contextmanager
from contextvars import ContextVar


_router_context = ContextVar(
    "router_context",
    default={
        "router_name": "unknown",
        "router_path": "unknown",
        "target_url": None,
        "phase": "unspecified",
    },
)


def format_router_log_prefix():
    context = _router_context.get()
    target_url = context.get("target_url")
    target_part = f" url={target_url}" if target_url else ""
    return (
        f"[router={context.get('router_name')} "
        f"path={context.get('router_path')} "
        f"phase={context.get('phase')}{target_part}]"
    )


def log_with_context(level, message, *args, exc_info=None):
    logging.log(level, "%s " + message, format_router_log_prefix(), *args, exc_info=exc_info)


@contextmanager
def router_log_context(router_name, router_path, phase, target_url=None):
    token = _router_context.set(
        {
            "router_name": router_name,
            "router_path": router_path,
            "phase": phase,
            "target_url": target_url,
        }
    )
    try:
        yield
    finally:
        _router_context.reset(token)
