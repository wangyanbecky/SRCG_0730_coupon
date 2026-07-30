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
        return and_(
            Campaign.status == "active",
            or_(
                Campaign.is_scheduled.is_(False),
                Campaign.is_scheduled.is_(None),
                and_(
                    Campaign.is_scheduled.is_(True),
                    or_(
                        Campaign.scheduled_time <= now,
                        and_(
                            Campaign.scheduled_time.is_(None),
                            Campaign.start_date <= now,
                        ),
                    ),
                ),
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
    def list_user_visible(cls, now):
        future_scheduled = and_(
            Campaign.status == "active",
            Campaign.is_scheduled.is_(True),
            Campaign.start_date <= Campaign.end_date,
            or_(
                Campaign.scheduled_time.is_(None),
                Campaign.scheduled_time <= Campaign.end_date,
            ),
            or_(
                Campaign.scheduled_time > now,
                Campaign.start_date > now,
            ),
        )
        currently_claimable = and_(
            Campaign.start_date <= now,
            cls.released_filter(now),
        )
        return (
            Campaign.query.filter(
                Campaign.end_date >= now,
                or_(currently_claimable, future_scheduled),
            )
            .order_by(Campaign.created_at.desc())
            .all()
        )

    @classmethod
    def is_released(cls, campaign, now):
        if campaign.status != "active":
            return False
        if not campaign.is_scheduled:
            return True
        release_time = campaign.release_time()
        return release_time is not None and release_time <= now

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
