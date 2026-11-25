from typing import Optional

from sqlalchemy.orm import Session

from app.core.enums import NotificationType
from app.models.notification import Notification


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        recipient_id: int,
        type: NotificationType,
        title: str,
        message: str,
        issue_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> Notification:
        notification = Notification(
            recipient_id=recipient_id,
            type=type,
            title=title,
            message=message,
            issue_id=issue_id,
            metadata_json=metadata,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification
