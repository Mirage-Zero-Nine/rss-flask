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
  - Default: `redis://localhost:6379/0`
  - This takes precedence over `config.yml`.

- `FLASK_APP`
  - Set in the Docker image as `app.py`.

- `FLASK_RUN_HOST`
  - Set in the Docker image as `0.0.0.0`.

### config.yml

You may place a `config.yml` file in the project root. Right now the only config value used by the app is:

```yaml
rss_redis_url: redis://localhost:6379/0
```

Notes:

- `RSS_REDIS_URL` overrides `config.yml` if both are set.
- If neither is set, the app falls back to `redis://localhost:6379/0`.

### Scheduler Configuration

The app starts a background scheduler to update router content automatically:

Global scheduler interval:

- Defined in utils/router_constants
- Current value: `10` minutes

Per-router cache refresh periods are defined in router constant files and are measured in milliseconds.

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
  -e RSS_REDIS_URL=redis://host.docker.internal:6379/0 \
  rss-flask:latest
```

If your Redis runs as another Docker container on the same custom Docker network, use that container name instead of `host.docker.internal`.

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
- If Redis is unavailable, cache reads and writes are skipped.
- The app also keeps an in-memory `last_build_time_cache` for per-process refresh timing.
- Restarting the process clears only the in-memory build-time cache, not the Redis data.

## Project Structure

- [app.py](/Users/oliverzh/IdeaProjects/rss-flask/app.py): Flask app entrypoint and route registration.
- [router/](/Users/oliverzh/IdeaProjects/rss-flask/router): Source-specific router implementations.
- [router_objects.py](/Users/oliverzh/IdeaProjects/rss-flask/router_objects.py): Instantiates router objects and shared feed metadata.
- [utils/cache_store.py](/Users/oliverzh/IdeaProjects/rss-flask/utils/cache_store.py): Redis cache integration.
- [utils/scheduler.py](/Users/oliverzh/IdeaProjects/rss-flask/utils/scheduler.py): Background refresh scheduler.
- [logs/](/Users/oliverzh/IdeaProjects/rss-flask/logs): File-based application logs.


