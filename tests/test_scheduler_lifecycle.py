"""Scheduler ownership during synchronous startup and interruption."""

import pytest

from utils import scheduler as module


class FakeScheduler:
    def __init__(self):
        self.running = False
        self.jobs = []
        self.shutdown_calls = []

    def start(self):
        self.running = True

    def shutdown(self, *, wait):
        self.shutdown_calls.append(wait)
        self.running = False

    def add_job(self, callback, **kwargs):
        self.jobs.append((callback, kwargs))


@pytest.fixture
def startup(monkeypatch):
    fake = FakeScheduler()
    released = []
    monkeypatch.setattr(module, "_scheduler_started", False)
    monkeypatch.setattr(module, "BackgroundScheduler", lambda **kwargs: fake)
    monkeypatch.setattr(module, "_load_scheduler_interval_minutes", lambda: 30)
    monkeypatch.setattr(module, "acquire_warm_lock", lambda name: True)
    monkeypatch.setattr(module, "release_warm_lock", released.append)
    return fake, released


def job(name, warmup, interval=10):
    return {"name": name, "warmup": warmup, "refresh": lambda: None,
            "interval_minutes": interval}


def test_interrupted_warmup_releases_lock_and_stops_unreturned_scheduler(startup):
    fake, released = startup
    interruption = KeyboardInterrupt()

    def interrupted():
        raise interruption

    with pytest.raises(KeyboardInterrupt) as caught:
        module.router_refresh_job_scheduler([
            job("/first", lambda: True), job("/interrupted", interrupted),
        ])
    assert caught.value is interruption
    assert released == ["/first", "/interrupted"]
    assert len(fake.jobs) == 1
    assert fake.shutdown_calls == [True]
    assert fake.running is False
    assert module._scheduler_started is False


def test_partial_scheduler_start_is_cleaned_up(startup, monkeypatch):
    fake, _ = startup

    def partial_start():
        fake.running = True
        raise SystemExit(7)

    monkeypatch.setattr(fake, "start", partial_start)
    with pytest.raises(SystemExit) as caught:
        module.router_refresh_job_scheduler([])
    assert caught.value.code == 7
    assert fake.shutdown_calls == [True]
    assert module._scheduler_started is False


def test_registration_failure_stops_scheduler_and_allows_retry(startup, monkeypatch):
    fake, released = startup
    original_add_job = fake.add_job

    def failed_registration(*args, **kwargs):
        raise RuntimeError("registration failed")

    monkeypatch.setattr(fake, "add_job", failed_registration)
    with pytest.raises(RuntimeError, match="registration failed"):
        module.router_refresh_job_scheduler([job("/sample", lambda: False)])
    assert released == ["/sample"]
    assert fake.shutdown_calls == [True]
    assert module._scheduler_started is False

    monkeypatch.setattr(fake, "add_job", original_add_job)
    assert module.router_refresh_job_scheduler([job("/sample", lambda: False)]) is fake
    assert module._scheduler_started is True


def test_ordinary_warmup_failure_keeps_existing_scheduling_behavior(startup):
    fake, released = startup

    def failed_warmup():
        raise ValueError("upstream failure")

    jobs = [job("/failing", failed_warmup, 5), job("/successful", lambda: True, 20)]
    assert module.router_refresh_job_scheduler(jobs) is fake
    assert released == ["/failing", "/successful"]
    assert [options["minutes"] for _, options in fake.jobs] == [5, 20]
    assert all(callback is module.run_refresh_job for callback, _ in fake.jobs)
    assert [options["args"] for _, options in fake.jobs] == [[jobs[0]], [jobs[1]]]
    assert fake.shutdown_calls == []
    assert module.router_refresh_job_scheduler(jobs) is None


def test_cleanup_failure_preserves_interruption_and_resets_guard(startup, monkeypatch, caplog):
    fake, _ = startup
    interruption = KeyboardInterrupt()

    def interrupted():
        raise interruption

    def failed_shutdown(**kwargs):
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(fake, "shutdown", failed_shutdown)
    with pytest.raises(KeyboardInterrupt) as caught:
        module.router_refresh_job_scheduler([job("/interrupted", interrupted)])
    assert caught.value is interruption
    assert module._scheduler_started is False
    assert "Scheduler cleanup failed after interrupted startup" in caplog.text
