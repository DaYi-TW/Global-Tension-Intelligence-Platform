from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "gtip",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url.replace("/1", "/2"),  # 用不同 DB 存 results
    include=["pipeline.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,           # Worker 完成後才 ack，防止任務遺失
    worker_prefetch_multiplier=1,  # 每次只取一個任務，避免長任務塞住短任務
)
