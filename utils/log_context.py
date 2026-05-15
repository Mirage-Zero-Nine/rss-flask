import contextvars
import logging


_current_router: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_router", default=None)


def set_current_router(router_path: str | None) -> contextvars.Token[str | None]:
    return _current_router.set(router_path or "unknown")


def reset_current_router(token: contextvars.Token[str | None]) -> None:
    _current_router.reset(token)


def get_current_router() -> str | None:
    return _current_router.get()


def log_external_fetch(method: str, link: str, **details: object) -> None:
    detail_string = " ".join(f"{key}={value}" for key, value in details.items() if value is not None)
    current_router = get_current_router()
    if current_router:
        logging.debug(
            "External fetch router=%s method=%s link=%s %s",
            current_router,
            method,
            link,
            detail_string
        )
    else:
        logging.debug(
            "External fetch method=%s link=%s %s",
            method,
            link,
            detail_string
        )
