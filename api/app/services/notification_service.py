"""Notification audience rules."""

from api.app.repositories import NotificationRepository


class NotificationService:
    @staticmethod
    def _selected_user_ids(raw_value):
        selected = set()
        for value in (raw_value or "").split(","):
            value = value.strip()
            if value.isdigit():
                selected.add(int(value))
        return selected

    @classmethod
    def visible_for_user(cls, user_id, limit=10):
        visible = []
        for notification in NotificationRepository.recent_candidates():
            if notification.target_type == "all" or (
                notification.target_type == "selected"
                and user_id in cls._selected_user_ids(notification.target_users)
            ):
                visible.append(notification)
                if len(visible) == limit:
                    break
        return visible
