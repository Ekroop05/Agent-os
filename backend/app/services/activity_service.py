from __future__ import annotations

from fastapi import HTTPException

from app.schemas import ActivityLog
from app.services.time_service import now_time


class ActivityService:
    def __init__(self):
        self.logs: dict[str, ActivityLog] = {}

    def list(self) -> list[ActivityLog]:
        return list(self.logs.values())

    def get(self, log_id: str) -> ActivityLog:
        log = self.logs.get(log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Activity log not found")
        return log

    def create(self, source: str, event_type: str, message: str, severity: str) -> ActivityLog:
        log_id = f"activity-{len(self.logs) + 1:03}"
        log = ActivityLog(
            id=log_id,
            timestamp=now_time(),
            source=source,
            type=event_type,
            message=message,
            severity=severity,
        )
        self.logs = {log_id: log, **self.logs}
        return log

    def update(self, log_id: str, **changes) -> ActivityLog:
        log = self.get(log_id)
        updated = log.model_copy(update={key: value for key, value in changes.items() if value is not None})
        self.logs[log_id] = updated
        return updated

    def delete(self, log_id: str) -> None:
        self.get(log_id)
        del self.logs[log_id]


activity_service = ActivityService()
