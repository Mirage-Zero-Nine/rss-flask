import logging

from werkzeug.exceptions import abort

from router.reuters.reuters_constants import is_valid_reuters_parameter
from router.zaobao.zaobao_realtime_router_constants import zaobao_region_parameter

from .feed_registry import DYNAMIC_FEED_ROUTES, STATIC_FEED_ROUTES, ZAOBAO_TITLE_FILTER


def register_routes(app):
    app.add_url_rule("/", endpoint="hello_world", view_func=hello_world)

    for definition in STATIC_FEED_ROUTES:
        app.add_url_rule(
            definition.path,
            endpoint=definition.endpoint,
            view_func=_build_static_feed_view(definition.router, definition.response_kwargs),
        )

    for definition in DYNAMIC_FEED_ROUTES:
        view_func = _build_dynamic_feed_view(definition)
        for rule in definition.rules:
            app.add_url_rule(
                rule.rule,
                endpoint=rule.endpoint,
                view_func=view_func,
                defaults=rule.defaults or None,
            )


def hello_world():
    return "Hello there."


def _build_static_feed_view(router, response_kwargs):
    def view():
        return router.get_rss_xml_response(**response_kwargs)

    view.__name__ = f"{router.__class__.__name__.lower()}_view"
    return view


def _build_dynamic_feed_view(definition):
    if definition.handler_type == "reuters":
        return _build_reuters_view(definition.router)
    if definition.handler_type == "zaobao":
        return _build_zaobao_view(definition.router)
    raise ValueError(f"Unsupported dynamic feed handler type: {definition.handler_type}")


def _build_reuters_view(router):
    def view(category, topic=None, limit=20):
        if is_valid_reuters_parameter(category, topic) is False:
            abort(404)

        parameters = {
            "category": category,
            "topic": topic,
            "limit": limit,
        }

        logging.info("category: %s, topic:%s", category, topic)
        return router.get_rss_xml_response(parameter=parameters)

    view.__name__ = f"{router.__class__.__name__.lower()}_dynamic_reuters_view"
    return view


def _build_zaobao_view(router):
    def view(region=None):
        if region is None:
            return router.get_rss_xml_response(parameter=None, title_filter=ZAOBAO_TITLE_FILTER)

        if region not in zaobao_region_parameter:
            abort(404)

        parameters = {
            "region": region,
        }
        return router.get_rss_xml_response(parameter=parameters, title_filter=ZAOBAO_TITLE_FILTER)

    view.__name__ = f"{router.__class__.__name__.lower()}_dynamic_zaobao_view"
    return view
