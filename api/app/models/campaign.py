"""Campaign model."""

from datetime import datetime

from api.app.extensions import db


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    initial_stock = db.Column(db.Integer, nullable=False, default=0)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    per_user_limit = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), nullable=False, default="draft")
    is_scheduled = db.Column(db.Boolean, default=False)
    scheduled_time = db.Column(db.DateTime, nullable=True)
    coupon_validity_days = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    creator = db.relationship("User", backref="campaigns_created", foreign_keys=[created_by])
    coupons = db.relationship("Coupon", backref="campaign", lazy="dynamic")
    reservations = db.relationship(
        "CampaignReservation",
        back_populates="campaign",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def release_time(self):
        """Return the effective time when a scheduled campaign can be claimed."""
        if not self.is_scheduled:
            return None
        candidates = [
            value for value in (self.scheduled_time, self.start_date) if value is not None
        ]
        return max(candidates) if candidates else None

    def is_pending_release_at(self, now=None):
        """Whether an active campaign is valid and waiting for scheduled release."""
        now = now or datetime.now()
        release_time = self.release_time()
        return (
            self.status == "active"
            and self.is_scheduled
            and release_time is not None
            and now < release_time <= self.end_date
        )

    def display_status_at(self, now=None):
        """Map a future scheduled campaign to the existing draft visual state."""
        return "draft" if self.is_pending_release_at(now) else self.status

    @property
    def claim_rate(self):
        if self.initial_stock == 0:
            return 0.0
        claimed = self.initial_stock - self.stock
        return round(claimed / self.initial_stock * 100, 1)

    @property
    def verify_rate(self):
        if self.initial_stock == 0:
            return 0.0
        verified = self.coupons.filter_by(status="verified").count()
        return round(verified / self.initial_stock * 100, 1)

    @property
    def is_active(self):
        now = datetime.now()
        return (
            self.status == "active"
            and self.start_date <= now <= self.end_date
            and self.stock > 0
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "amount": self.amount,
            "stock": self.stock,
            "initial_stock": self.initial_stock,
            "start_date": self.start_date.strftime("%Y-%m-%d %H:%M"),
            "end_date": self.end_date.strftime("%Y-%m-%d %H:%M"),
            "per_user_limit": self.per_user_limit,
            "description": self.description,
            "status": self.status,
            "claim_rate": self.claim_rate,
            "verify_rate": self.verify_rate,
            "coupon_validity_days": self.coupon_validity_days,
        }

    def __repr__(self):
        return f"<Campaign {self.name} stock={self.stock}>"
