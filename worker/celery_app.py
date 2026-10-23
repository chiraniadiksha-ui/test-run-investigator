from celery import Celery


celery_app = Celery(
    "test_run_investigator",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
)