"""ORM-to-DTO gateway for the standalone AI package."""

from datetime import datetime, timedelta

from ai import Campaign as CampaignDTO
from ai import CouponAIService, RiskHistoryEntry, UserProfile
from sqlalchemy import update

from api.app.extensions import db
from api.app.models import RiskLog, User
from api.config import Config


class AIGateway:
    """Expose the legacy Flask-facing AI interface over the root AI service."""

    def __init__(self, service=None):
        self._service = service or CouponAIService()

    @property
    def status(self):
        return self._service.status

    def list_text_models(self):
        return self._service.list_text_models()

    def recommend_coupons(self, user, campaigns):
        if not campaigns:
            return []

        user_profile = UserProfile(
            age=user.age,
            gender=user.gender or "",
            hobbies=tuple(
                item.strip() for item in (user.hobbies or "").split(",") if item.strip()
            ),
            occupation=user.occupation or "",
            points=user.points or 0,
        )
        now = datetime.now()
        campaign_dtos = [
            CampaignDTO(
                campaign_id=campaign.id,
                name=campaign.name,
                amount=campaign.amount,
                stock=campaign.stock,
                days_left=(campaign.end_date - now).days if campaign.end_date else 0,
                description=campaign.description or "",
            )
            for campaign in campaigns
        ]
        recommendations = self._service.recommend_coupons(user_profile, campaign_dtos)
        campaign_map = {campaign.id: campaign for campaign in campaigns}
        campaign_map.update({str(campaign.id): campaign for campaign in campaigns})

        ranked = []
        for item in recommendations:
            campaign = campaign_map.get(item.get("campaign_id"))
            if campaign is not None:
                ranked.append(
                    {
                        "campaign": campaign,
                        "reason": item.get("reason", "为您精选推荐"),
                        "score": item.get("score", 0.5),
                    }
                )
        return ranked

    def assess_risk(self, user, action):
        # Serialize risk checks for the same user without changing persisted data.
        # This makes the subsequent count-plus-current-request decision atomic on
        # both SQLite (database write lock) and row-locking database engines.
        db.session.execute(
            update(User).where(User.id == user.id).values(points=User.points),
            execution_options={"synchronize_session": False},
        )

        recent_logs = (
            RiskLog.query.filter_by(user_id=user.id)
            .order_by(RiskLog.created_at.desc())
            .limit(10)
            .all()
        )
        history = tuple(
            RiskHistoryEntry(
                action=log.action,
                risk_score=log.risk_score or 0.0,
                decision=log.decision,
                time=log.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if log.created_at
                else "",
            )
            for log in recent_logs
        )

        window_start = datetime.now() - timedelta(
            seconds=Config.RISK_CLAIM_WINDOW_SECONDS
        )
        previous_count = RiskLog.query.filter(
            RiskLog.user_id == user.id,
            RiskLog.action == action,
            RiskLog.created_at >= window_start,
        ).count()
        recent_count = previous_count + 1

        result = self._service.assess_risk(
            {
                "username": user.username,
                "age": user.age,
                "points": user.points,
                "created_at": user.created_at.strftime("%Y-%m-%d")
                if user.created_at
                else "",
            },
            action=action,
            recent_history=history,
            recent_count=recent_count,
        )

        maximum = Config.RISK_MAX_CLAIMS_IN_WINDOW
        if recent_count >= maximum:
            return {
                "risk_score": round(min(recent_count / maximum, 1.0), 2),
                "decision": "block",
                "reason": (
                    f"检测到异常高频操作：{Config.RISK_CLAIM_WINDOW_SECONDS}秒内"
                    f"{recent_count}次{action}请求"
                ),
            }
        return result


ai_gateway = AIGateway()
