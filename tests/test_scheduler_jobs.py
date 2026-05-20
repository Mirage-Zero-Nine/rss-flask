from application.scheduler_jobs import build_scheduler_jobs
from application.router_dependencies import (
    apnews_business_router_path,
    apnews_router_path,
)


def _job_index(jobs, name):
    for index, job in enumerate(jobs):
        if job["name"] == name:
            return index
    raise AssertionError(f"job '{name}' not found in scheduler jobs")


def test_apnews_business_warmup_runs_before_apnews_top():
    """/apnews/top dedups against /apnews/business cached metadata.

    For dedup to apply on cold start, /apnews/business must populate its
    metadata cache before /apnews/top runs. Otherwise the first refresh
    of /apnews/top sees no business metadata and publishes the unfiltered
    list; because write_metadata_list merges new entries with existing
    ones, any business article that slips into /apnews/top during the
    cold-start window can persist across subsequent refreshes.
    """
    jobs = build_scheduler_jobs()
    business_index = _job_index(jobs, apnews_business_router_path)
    top_index = _job_index(jobs, apnews_router_path)

    assert business_index < top_index, (
        f"apnews_business at index {business_index} must run before "
        f"apnews_top at index {top_index}"
    )


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
