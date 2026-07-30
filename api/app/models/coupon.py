"""Coupon model."""

from datetime import datetime

from api.app.extensions import db


class Coupon(db.Model):
    __tablename__ = "coupons"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(
        db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="claimed")
    claimed_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    verifier = db.relationship("User", backref="verifications", foreign_keys=[verified_by])

    @property
    def effective_expiry(self):
        if self.expires_at:
            return self.expires_at
        if self.campaign:
            return self.campaign.end_date
        return None

    @property
    def is_expired(self):
        expiry = self.effective_expiry
        return expiry is not None and datetime.now() > expiry

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign.name if self.campaign else "",
            "user_id": self.user_id,
            "code": self.code,
            "status": self.status,
            "claimed_at": self.claimed_at.strftime("%Y-%m-%d %H:%M:%S") if self.claimed_at else "",
            "expires_at": self.expires_at.strftime("%Y-%m-%d %H:%M:%S") if self.expires_at else "",
            "verified_at": self.verified_at.strftime("%Y-%m-%d %H:%M:%S") if self.verified_at else "",
        }

    def __repr__(self):
        return f"<Coupon {self.code} ({self.status})>"
