"""
Celery Beat 排程設定
對應 docs/09-scheduler-worker.md §9.3
"""

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "ingest-gdelt": {
        "task": "pipeline.tasks.ingest_gdelt",
        "schedule": 900,                          # 每 15 分鐘
    },
    "ingest-acled": {
        "task": "pipeline.tasks.ingest_acled",
        "schedule": crontab(minute=5),            # 每小時 :05
    },
    "ingest-news": {
        "task": "pipeline.tasks.ingest_news",
        "schedule": crontab(minute=10),           # 每小時 :10
    },
    "normalize-pending": {
        "task": "pipeline.tasks.normalize_pending",
        "schedule": 1200,                         # 每 20 分鐘
    },
    "ai-enrich-pending": {
        "task": "pipeline.tasks.ai_enrich_pending",
        "schedule": 1800,                         # 每 30 分鐘
    },
    "score-and-aggregate": {
        "task": "pipeline.tasks.score_and_aggregate",
        "schedule": crontab(minute=55),           # 每小時 :55（確保 AI 分析有時間完成）
    },
    "daily-summary": {
        "task": "pipeline.tasks.daily_summary_gen",
        "schedule": crontab(hour=6, minute=0),    # 每日 06:00 UTC
    },
    "weekly-full-recalculate": {
        "task": "pipeline.tasks.full_recalculate",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),  # 每週日 02:00 UTC
    },
    "daily-cleanup": {
        "task": "pipeline.tasks.cleanup_old_cache",
        "schedule": crontab(hour=3, minute=0),    # 每日 03:00 UTC
    },
}
