"""Database access for campaigns."""

from sqlalchemy import and_, or_, update

from api.app.extensions import db
from api.app.models import Campaign


class CampaignRepository:
    @staticmethod
    def get(campaign_id):
        return db.session.get(Campaign, campaign_id)

    @staticmethod
    def released_filter(now):
        return or_(
            Campaign.status == "active",
            and_(
                Campaign.is_scheduled.is_(True),
                Campaign.scheduled_time.is_not(None),
                Campaign.scheduled_time <= now,
            ),
        )

    @classmethod
    def list_claimable(cls, now):
        return (
            Campaign.query.filter(
                Campaign.start_date <= now,
                Campaign.end_date >= now,
                cls.released_filter(now),
            )
            .order_by(Campaign.created_at.desc())
            .all()
        )

    @classmethod
    def is_released(cls, campaign, now):
        return campaign.status == "active" or (
            campaign.is_scheduled
            and campaign.scheduled_time is not None
            and campaign.scheduled_time <= now
        )

    @classmethod
    def decrement_stock(cls, campaign_id, now):
        result = db.session.execute(
            update(Campaign)
            .where(
                Campaign.id == campaign_id,
                Campaign.stock > 0,
                Campaign.start_date <= now,
                Campaign.end_date >= now,
                cls.released_filter(now),
            )
            .values(stock=Campaign.stock - 1),
            execution_options={"synchronize_session": False},
        )
        return result.rowcount == 1
