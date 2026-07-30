"""Persistent user reservation for a future coupon campaign."""

from datetime import datetime

from api.app.extensions import db


class CampaignReservation(db.Model):
    __tablename__ = "campaign_reservations"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "campaign_id",
            name="uq_campaign_reservation_user_campaign",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id = db.Column(
        db.Integer,
        db.ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    user = db.relationship("User", back_populates="campaign_reservations")
    campaign = db.relationship("Campaign", back_populates="reservations")

    def __repr__(self):
        return f"<CampaignReservation user={self.user_id} campaign={self.campaign_id}>"
