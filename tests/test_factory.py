"""Tests for application.factory.should_start_scheduler.

The Flask debug reloader spawns two processes; the scheduler must only start
in the child process (signaled by WERKZEUG_RUN_MAIN=true). In production
(no FLASK_DEBUG) the scheduler should always start.
"""

from application.factory import should_start_scheduler


def test_should_start_scheduler_true_when_werkzeug_run_main_is_true(monkeypatch):
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
    monkeypatch.setenv("FLASK_DEBUG", "1")  # would skip on its own, but RUN_MAIN wins

    assert should_start_scheduler() is True


def test_should_start_scheduler_false_in_flask_debug_parent_process(monkeypatch):
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    monkeypatch.setenv("FLASK_DEBUG", "1")

    assert should_start_scheduler() is False


def test_should_start_scheduler_true_in_production_when_no_debug(monkeypatch):
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    monkeypatch.delenv("FLASK_DEBUG", raising=False)

    assert should_start_scheduler() is True


def test_should_start_scheduler_true_when_flask_debug_not_one(monkeypatch):
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    monkeypatch.setenv("FLASK_DEBUG", "0")

    assert should_start_scheduler() is True
