# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

WORKDIR /python-docker

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV RSS_REDIS_URL=redis://redis-cache:6379/0

RUN mkdir -p /logs

RUN playwright install chromium && \
    playwright install-deps chromium
CMD ["flask", "run"]
