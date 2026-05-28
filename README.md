# rss-flask

## How to Run

Create a Python 3.12 virtual environment and install dependencies:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the Flask app:

```bash
flask run
```

Or run the entry point directly:

```bash
python app.py
```

Redis is required for normal application use. Running without Redis is only useful for local debugging; routes serve empty feeds and cache writes are skipped.

## Configuration

Supported configuration values:

- `RSS_REDIS_URL`
- `RSS_SCHEDULER_REFRESH_PERIOD_MINUTES`
- `rss_redis_url` in `config.yml`
- `scheduler_refresh_period_in_minutes` in `config.yml`
- `router_refresh_periods` in `config.yml` - per-router refresh period in minutes

Environment variables take precedence over `config.yml`.

### Full `config.yml` Example

```yaml
# rss-flask configuration
# Env vars take precedence over values in this file.
# All keys are optional - defaults are used when missing.

rss_redis_url: "redis://localhost:6379/0"
scheduler_refresh_period_in_minutes: 15

# Per-router refresh period in minutes.
# Each router checks this cooldown before fetching upstream content.
router_refresh_periods:
  cnbeta: 10
  dayone: 60
  earthquake: 15
  embassy: 10
  jandan: 60
  meta_blog: 30
  reuters: 30
  sar: 30
  wsdot: 30
  zaobao: 10
  apnews_top: 15
  apnews_business: 15
  apple_developer_news: 60
  apple_newsroom: 60
```

If a key is missing, the router falls back to its hardcoded default.

## Development Checks

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
python -m pytest
```

Run static type checking:

```bash
python -m pyright
```

## Description

`rss-flask` is a Flask service that converts upstream websites and feeds into stable RSS XML endpoints. Each router targets one source, normalizes article metadata and content, stores the result in Redis, and serves RSS from cache.

## Cache Model

Redis stores three kinds of data:

- Metadata list per feed variant.
- Article content payload per article.
- Last-build timestamp per feed variant.

Cache keys are derived from router path plus optional route parameters.

Examples:

- `router_cache:cnbeta:...`
- `router_cache:zaobao-realtime-world:...`
- `router_cache:apnews-top:...`

## Scheduler

The scheduler is APScheduler-based and runs inside the Flask process.

There are two timing layers:

- Global scheduler interval: `RSS_SCHEDULER_REFRESH_PERIOD_MINUTES` or `scheduler_refresh_period_in_minutes`.
- Per-router upstream cooldown: each router has its own `period` in milliseconds.

The global scheduler determines how often jobs are considered. The router-level `period` determines whether that router actually refetches upstream content or keeps serving the existing cache.

The current default global scheduler interval is `15` minutes.

## Active Endpoints

Current route families include:

- `/cnbeta`
- `/dayone`
- `/earthquake`
- `/embassy`
- `/jandan`
- `/meta/blog`
- `/reuters/<category>` where `<category>` is `world` or `business`
- `/sar`
- `/wsdot/news`
- `/zaobao/realtime/<region>` where `<region>` is `china` or `world`
- `/apnews/top`
- `/apnews/business`
- `/apple/developer`
- `/apple/newsroom`

### Parameterized Routes

- Reuters supports the `/reuters/<category>` route with `world` or `business`. Top-level `world` and `business` feeds are gap-filled from Yahoo Reuters by a scheduler-only secondary source. Topic-level routes such as `/reuters/world/asia-pacific` are not supported.
- Zaobao supports region-specific feeds for `china` and `world`.
