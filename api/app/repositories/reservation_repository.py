"""Database access for campaign reservations."""

from sqlalchemy.exc import IntegrityError

from api.app.extensions import db
from api.app.models import CampaignReservation


class ReservationRepository:
    @staticmethod
    def campaign_ids_for_user(user_id):
        return {
            campaign_id
            for (campaign_id,) in db.session.query(
                CampaignReservation.campaign_id
            ).filter_by(user_id=user_id)
        }

    @staticmethod
    def get(user_id, campaign_id):
        return CampaignReservation.query.filter_by(
            user_id=user_id,
            campaign_id=campaign_id,
        ).first()

    @classmethod
    def add_idempotent(cls, user_id, campaign_id):
        existing = cls.get(user_id, campaign_id)
        if existing is not None:
            return existing, False

        reservation = CampaignReservation(
            user_id=user_id,
            campaign_id=campaign_id,
        )
        db.session.add(reservation)
        try:
            db.session.commit()
            return reservation, True
        except IntegrityError:
            db.session.rollback()
            existing = cls.get(user_id, campaign_id)
            if existing is None:
                raise
            return existing, False
