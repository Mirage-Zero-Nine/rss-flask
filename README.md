# rss-flask

`rss-flask` is a Flask service that turns several websites and feeds into RSS endpoints. Each endpoint fetches content from an upstream source, converts it into RSS XML, and returns it from a stable route that you can subscribe to in an RSS reader.

The project utlize Redis to cache feed metadata and article content.

## Runtime Requirements

- Python 3.12 for the Docker image.
- Redis for cache storage.

The Docker image is currently based on Python 3.12:

```dockerfile
FROM python:3.12-slim-bookworm
```

## Configuration

The app has a small configuration surface today.

### Environment Variables

- `RSS_REDIS_URL`
  - Redis connection string used for cache storage.
  - Local default outside Docker: `redis://localhost:6379/0`
  - Docker default in the image: `redis://redis-cache:6379/0`
  - This takes precedence over `config.yml`.

- `RSS_SCHEDULER_REFRESH_PERIOD_MINUTES`
  - Global scheduler interval in minutes.
  - Overrides `scheduler_refresh_period_in_minutes` in `config.yml`.
  - Default: `10`

- `FLASK_APP`
  - Set in the Docker image as `app.py`.

- `FLASK_RUN_HOST`
  - Set in the Docker image as `0.0.0.0`.

### config.yml

You may place a `config.yml` file in the project root. Supported values:

```yaml
rss_redis_url: redis://localhost:6379/0
scheduler_refresh_period_in_minutes: 10
```

Notes:

- `RSS_REDIS_URL` overrides `config.yml` if both are set.
- `RSS_SCHEDULER_REFRESH_PERIOD_MINUTES` overrides `config.yml` if both are set.
- If neither is set, the app falls back to `redis://localhost:6379/0`.

### Scheduler Configuration

The app starts a background scheduler to update router content automatically:

Global scheduler interval:

- Config key: `scheduler_refresh_period_in_minutes`
- Env override: `RSS_SCHEDULER_REFRESH_PERIOD_MINUTES`
- Default: `10` minutes

Per-router cache refresh periods are defined in router constant files and are measured in milliseconds.
Warm-up runs once at startup and populates Redis for scheduled routers only when their cache is empty.

## Start With Docker

### 1. Build the image

```bash
docker build -t rss-flask .
```

### 2. Run Redis

If you already have Redis somewhere else, point `RSS_REDIS_URL` at it and skip this step.

Example local Redis container:

```bash
docker run -d --name rss-flask-redis -p 6379:6379 redis:7
```

### 3. Run the app container

```bash
docker run -d \
  --restart=always \
  --name rss-flask \
  -p 5000:5000 \
  --network rss-net \
  -e RSS_REDIS_URL=redis://redis-cache:6379/0 \
  -e RSS_SCHEDULER_REFRESH_PERIOD_MINUTES=10 \
  rss-flask:latest
```

This matches a Redis container named `redis-cache` on the `rss-net` network.

### 4. Open a feed

Example:

```text
http://localhost:5000/cnbeta
```

## Start Locally

This project can also be run directly with Python if you want to develop without Docker.

### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Start Redis

Make sure Redis is available at the URL you plan to use.

Example:

```bash
export RSS_REDIS_URL=redis://localhost:6379/0
export RSS_SCHEDULER_REFRESH_PERIOD_MINUTES=10
```

### 4. Run Flask

```bash
flask --app app.py run
```

Or:

```bash
python3 app.py
```

The default local address is typically:

```text
http://127.0.0.1:5000
```

## Cache Behavior

- Router metadata lists and article payloads are stored in Redis.
- Router last-build timestamps are also stored in Redis.
- If Redis is unavailable, cache reads and writes are skipped.
- Restarting the process does not clear cached router state as long as Redis keeps the data.
- Client API requests read only from Redis and do not fetch upstream websites.
- Scheduler jobs are responsible for upstream refreshes and startup warm-up.

## Logging

- The app logs at `DEBUG` level.
- External fetch logs include the router path and target link to help trace scheduler refreshes and article retrieval failures.
- Scheduler logs include job registration, warm-up, refresh, and exception details.

