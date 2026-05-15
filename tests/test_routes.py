from application.factory import create_app


class StubRouter:
    VALID_TOPICS = {"world"}
    VALID_CATEGORIES = {"all": None, "research": "Research"}

    def __init__(self):
        self.calls = []

    def get_rss_xml_response(self, **kwargs):
        self.calls.append(kwargs)
        return "rss"


def test_health_check():
    app = create_app()

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert response.text == "Hello there."


def test_reuters_rejects_invalid_category():
    app = create_app()

    response = app.test_client().get("/reuters/not-a-category")

    assert response.status_code == 404


def test_reuters_passes_valid_parameters(monkeypatch):
    app = create_app()
    stub = StubRouter()
    monkeypatch.setattr("application.routes.reuters_news", stub)

    response = app.test_client().get("/reuters/world/asia-pacific/5")

    assert response.status_code == 200
    assert stub.calls == [{"parameter": {"category": "world", "topic": "asia-pacific", "limit": 5}}]


def test_zaobao_rejects_invalid_region():
    app = create_app()

    response = app.test_client().get("/zaobao/realtime/mars")

    assert response.status_code == 404


def test_yahoo_rejects_invalid_topic(monkeypatch):
    app = create_app()
    monkeypatch.setattr("application.routes.yahoo_news", StubRouter())

    response = app.test_client().get("/yahoo/reuters/invalid")

    assert response.status_code == 404


def test_yahoo_passes_lowercase_topic(monkeypatch):
    app = create_app()
    stub = StubRouter()
    monkeypatch.setattr("application.routes.yahoo_news", stub)

    response = app.test_client().get("/yahoo/reuters/World")

    assert response.status_code == 200
    assert stub.calls == [{"parameter": {"topic": "world"}}]


def test_openai_news_rejects_missing_category(monkeypatch):
    app = create_app()
    monkeypatch.setattr("application.routes.openai_news", StubRouter())

    response = app.test_client().get("/openai-news")

    assert response.status_code == 404


def test_openai_news_rejects_invalid_category(monkeypatch):
    app = create_app()
    monkeypatch.setattr("application.routes.openai_news", StubRouter())

    response = app.test_client().get("/openai-news/invalid")

    assert response.status_code == 404


def test_openai_news_passes_lowercase_category(monkeypatch):
    app = create_app()
    stub = StubRouter()
    monkeypatch.setattr("application.routes.openai_news", stub)

    response = app.test_client().get("/openai-news/Research")

    assert response.status_code == 200
    assert stub.calls == [{"parameter": {"category": "research"}}]
