"""Notification model."""

from datetime import datetime

from api.app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.String(20), nullable=False, default="all")
    target_users = db.Column(db.Text, default="")
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    creator = db.relationship("User", backref="notifications_sent", foreign_keys=[created_by])

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "target_type": self.target_type,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
            "creator": self.creator.username if self.creator else "",
        }
