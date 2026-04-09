from celery import Celery

from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "software_factory",
    broker=str(settings.celery_broker_url),
    backend=str(settings.celery_result_backend),
    include=["infrastructure.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
)

