# rss-flask

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
- `/reuters/<category>[/<topic>[/<limit>]]`
- `/sar`
- `/wsdot/news`
- `/zaobao/realtime/<region>`
- `/apnews/top`
- `/apnews/business`

### Parameterized Routes

- Reuters supports categories such as `world` and `business`, with optional topic and limit parameters.
- Zaobao supports a general realtime feed plus region-specific feeds such as `china` and `world`.

## Configuration

Supported configuration values:

- `RSS_REDIS_URL`
- `RSS_SCHEDULER_REFRESH_PERIOD_MINUTES`
- `rss_redis_url` in `config.yml`
- `scheduler_refresh_period_in_minutes` in `config.yml`
- `router_refresh_periods` in `config.yml` — per-router refresh period in minutes

Environment variables take precedence over `config.yml`.

### Full `config.yml` Example

```yaml
# rss-flask configuration
# Env vars take precedence over values in this file.
# All keys are optional — defaults are used when missing.

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
```

If a key is missing, the router falls back to its hardcoded default.