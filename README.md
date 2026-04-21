# rss-flask

## What Is This?

`rss-flask` is a Flask service that converts several websites and APIs into RSS feeds.

The app now uses:
- Flask app factory and separated route registration
- Redis for cache storage
- Docker for deployment

## Runtime Requirements

- Python 3.13 for the Docker image
- Redis for cache storage

Redis is required at app startup. The service stores:
- router metadata lists
- fetched article payloads
- feed build timestamps

Client requests are cache-only:
- RSS routes read from Redis only
- upstream websites/APIs are fetched by the background scheduler
- a cold cache returns an empty RSS feed until the scheduler populates it

## Redis Configuration

Set Redis with either:
- environment variable: `RSS_REDIS_URL`
- `config.yml` with `rss_redis_url`

`RSS_REDIS_URL` takes precedence.

Default:
```yaml
rss_redis_url: redis://localhost:6379/0
```

Example environment variable:
```bash
export RSS_REDIS_URL=redis://localhost:6379/0
```

## Docker Deployment

### 1. Build The Image

```bash
docker build -t YOUR_IMAGE_NAME .
```

### 2. Create Or Reuse A Docker Network

If the app container and Redis container run in Docker together, they should share the same user-defined network.

Example:
```bash
docker network create rss-net
```

### 3. Start Redis

If Redis is not already running:

```bash
docker run -d \
  --name redis-cache \
  --network rss-net \
  redis:7
```

If you already have a Redis container, confirm both containers are on the same network:

```bash
docker inspect redis-cache --format '{{json .NetworkSettings.Networks}}'
docker inspect YOUR_APP_CONTAINER --format '{{json .NetworkSettings.Networks}}'
```

If needed:

```bash
docker network connect rss-net redis-cache
docker network connect rss-net YOUR_APP_CONTAINER
```

### 4. Start The App

For a Redis container named `redis-cache` on network `rss-net`:

```bash
docker run -d \
  --restart=always \
  --name YOUR_APP_CONTAINER \
  --network rss-net \
  -p 5000:5000 \
  -e RSS_REDIS_URL=redis://redis-cache:6379/0 \
  YOUR_IMAGE_NAME:latest
```

Then access feeds at:

```text
http://localhost:5000/PATH_TO_ROUTER
```

## Local Development

Install dependencies:

```bash
./venv/bin/pip install -r requirements.txt
```

Run with Redis available:

```bash
export RSS_REDIS_URL=redis://localhost:6379/0
./venv/bin/flask --app app run
```

## Routes

Routes are registered in `rss_flask/routes.py`.

Common feed paths:
- `/cnbeta`
- `/dayone`
- `/earthquake`
- `/embassy`
- `/jandan`
- `/meta/blog`
- `/nbc/top`
- `/reuters/<category>`
- `/reuters/<category>/<topic>`
- `/reuters/<category>/<topic>/<limit>`
- `/sar`
- `/theverge`
- `/twitter/blog`
- `/wsdot/news`
- `/zaobao/realtime/<region>`
- `/zhihu/daily`

### Route Parameters

- `/zaobao/realtime/<region>` supports `world` and `china`

## Project Structure

- `app.py`: minimal entrypoint
- `rss_flask/app_factory.py`: Flask app creation and startup wiring
- `rss_flask/routes.py`: route registration
- `rss_flask/feed_registry.py`: router registry and router construction
- `router/`: source-specific router implementations
- `utils/cache_store.py`: Redis cache integration
- `utils/http_client.py`: shared HTTP fetching helpers
- `utils/helpers.py`: shared helper and time conversion functions

## Scheduler

The background scheduler is the only component that fetches upstream content.

Each scheduled router job has its own interval. The interval is currently derived from the router definition period, and can also be overridden per router in `rss_flask/feed_registry.py`.

Configuration is in:
- `utils/scheduler.py`
- `rss_flask/feed_registry.py`
- `rss_flask/route_config.py`

## Notes

- The service no longer uses local JSON files under `data/` for cache storage.
- The `data/` directory has been removed from the repo.
- If Redis is unreachable, the app will fail to start.
