# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.14-slim-trixie
FROM ${PYTHON_IMAGE}

WORKDIR /python-docker

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV RSS_REDIS_URL=redis://redis-cache:6379/0
ENV RSS_LOG_DIR=/logs

RUN groupadd --gid 10001 rss && useradd --uid 10001 --gid 10001 --no-create-home rss && \
    mkdir -p /logs && chown 10001:10001 /logs

USER 10001:10001
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=8s --start-period=600s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:5000/health/ready', timeout=5).close()"]
CMD ["python", "-m", "application.server"]
