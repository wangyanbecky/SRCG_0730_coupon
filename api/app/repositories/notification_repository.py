"""Database access for notifications."""

from api.app.models import Notification


class NotificationRepository:
    @staticmethod
    def recent_candidates(limit=100):
        return (
            Notification.query.order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )
