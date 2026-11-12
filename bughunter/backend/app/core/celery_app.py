"""Celery application configured with Redis broker and result backend."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "bughunter",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task behaviour
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Result expiry (24 h)
    result_expires=86400,
    # Retry policy
    task_max_retries=3,
    task_default_retry_delay=10,
    # Routes
    task_routes={
        "app.workers.tasks.run_subdomain_scan": {"queue": "scans"},
        "app.workers.tasks.run_probe_scan": {"queue": "scans"},
        "app.workers.tasks.run_crawl_scan": {"queue": "scans"},
        "app.workers.tasks.run_vuln_scan": {"queue": "scans"},
        "app.workers.tasks.run_ai_analysis": {"queue": "ai"},
    },
)
