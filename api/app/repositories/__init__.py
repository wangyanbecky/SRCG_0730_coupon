"""Repository exports for database access."""

from api.app.repositories.campaign_repository import CampaignRepository
from api.app.repositories.coupon_repository import CouponRepository
from api.app.repositories.notification_repository import NotificationRepository

__all__ = ["CampaignRepository", "CouponRepository", "NotificationRepository"]
