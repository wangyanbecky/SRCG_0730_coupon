"""Database access for coupons."""

from sqlalchemy import func

from api.app.extensions import db
from api.app.models import Coupon


class CouponRepository:
    @staticmethod
    def count_for_user_campaign(user_id, campaign_id):
        return Coupon.query.filter_by(
            user_id=user_id,
            campaign_id=campaign_id,
        ).count()

    @staticmethod
    def counts_for_user(user_id, campaign_ids):
        if not campaign_ids:
            return {}
        rows = (
            db.session.query(Coupon.campaign_id, func.count(Coupon.id))
            .filter(
                Coupon.user_id == user_id,
                Coupon.campaign_id.in_(campaign_ids),
            )
            .group_by(Coupon.campaign_id)
            .all()
        )
        return {campaign_id: count for campaign_id, count in rows}

    @staticmethod
    def list_for_user(user_id):
        return (
            Coupon.query.filter_by(user_id=user_id)
            .order_by(Coupon.claimed_at.desc())
            .all()
        )

    @staticmethod
    def list_claimed_for_user(user_id):
        return Coupon.query.filter_by(user_id=user_id, status="claimed").all()

    @staticmethod
    def add(coupon):
        db.session.add(coupon)
