"""Risk audit log model."""

from datetime import datetime

from api.app.extensions import db


class RiskLog(db.Model):
    __tablename__ = "risk_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    risk_score = db.Column(db.Float, default=0.0)
    decision = db.Column(db.String(20), nullable=False, default="allow")
    reason = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", backref="risk_logs", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else "",
            "action": self.action,
            "risk_score": round(self.risk_score, 2),
            "decision": self.decision,
            "reason": self.reason,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }
