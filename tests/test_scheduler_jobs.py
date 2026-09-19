from application.scheduler_jobs import build_scheduler_jobs


def test_apnews_jobs_removed():
    jobs = build_scheduler_jobs()
    assert not any(job["name"].startswith("/apnews") for job in jobs)


def test_scheduler_jobs_have_unique_names():
    jobs = build_scheduler_jobs()
    names = [job["name"] for job in jobs]
    assert len(names) == len(set(names)), f"duplicate job names: {names}"


def test_scheduler_jobs_each_have_warmup_and_refresh_callables():
    jobs = build_scheduler_jobs()
    assert jobs, "expected at least one scheduler job"
    for job in jobs:
        assert callable(job.get("warmup")), f"job {job['name']} missing warmup"
        assert callable(job.get("refresh")), f"job {job['name']} missing refresh"
