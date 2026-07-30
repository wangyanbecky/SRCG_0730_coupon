"""Coupon discovery and atomic claiming business rules."""

import uuid
from datetime import datetime, timedelta

from api.app.extensions import db
from api.app.models import Coupon, RiskLog
from api.app.repositories import CampaignRepository, CouponRepository
from api.app.services.ai_gateway import ai_gateway
from api.config import Config


class ClaimError(Exception):
    def __init__(self, message, error_type, status_code=400, risk_blocked=False):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.risk_blocked = risk_blocked

    def to_dict(self):
        result = {
            "success": False,
            "message": self.message,
            "error_type": self.error_type,
        }
        if self.risk_blocked:
            result["risk_blocked"] = True
        return result


class CouponService:
    @staticmethod
    def list_claimable_campaigns(now=None):
        return CampaignRepository.list_claimable(now or datetime.now())

    @staticmethod
    def list_user_visible_campaigns(now=None):
        return CampaignRepository.list_user_visible(now or datetime.now())

    @staticmethod
    def claimed_counts(user_id, campaigns):
        return CouponRepository.counts_for_user(
            user_id,
            [campaign.id for campaign in campaigns],
        )

    @staticmethod
    def list_user_coupons(user_id):
        return CouponRepository.list_for_user(user_id)

    @staticmethod
    def near_expiry(user_id, now=None, days=3):
        now = now or datetime.now()
        threshold = now + timedelta(days=days)
        return [
            coupon
            for coupon in CouponRepository.list_claimed_for_user(user_id)
            if coupon.effective_expiry is not None
            and now <= coupon.effective_expiry <= threshold
        ]

    @classmethod
    def claim(cls, campaign_id, user, now=None):
        now = now or datetime.now()
        campaign = CampaignRepository.get(campaign_id)
        if campaign is None:
            raise ClaimError("活动不存在。", "not_found", 404)
        if campaign.is_pending_release_at(now):
            raise ClaimError("未到领取时间。", "campaign_not_started")
        if not CampaignRepository.is_released(campaign, now):
            raise ClaimError("该活动未开放领取。", "campaign_unavailable")
        if now < campaign.start_date:
            raise ClaimError("该活动尚未开始。", "campaign_not_started")
        if now > campaign.end_date:
            raise ClaimError("该活动已结束。", "campaign_ended")

        try:
            risk = ai_gateway.assess_risk(user, "claim_coupon")
            db.session.refresh(user)
            db.session.add(
                RiskLog(
                    user_id=user.id,
                    action="claim_coupon",
                    risk_score=risk["risk_score"],
                    decision=risk["decision"],
                    reason=risk["reason"],
                )
            )
            if risk["decision"] == "block":
                db.session.commit()
                raise ClaimError(
                    f'操作被拦截：{risk["reason"]}',
                    "risk_blocked",
                    403,
                    risk_blocked=True,
                )

            db.session.flush()
            if (
                CouponRepository.count_for_user_campaign(user.id, campaign_id)
                >= campaign.per_user_limit
            ):
                db.session.commit()
                raise ClaimError("您已达到该活动的领取上限。", "limit_exceeded")

            if not CampaignRepository.decrement_stock(campaign_id, now):
                db.session.commit()
                raise ClaimError("优惠券已被抢光！", "out_of_stock")

            coupon_code = f"CPN-{uuid.uuid4().hex[:8].upper()}"
            expires_at = (
                now + timedelta(days=campaign.coupon_validity_days)
                if campaign.coupon_validity_days
                else None
            )
            CouponRepository.add(
                Coupon(
                    campaign_id=campaign_id,
                    user_id=user.id,
                    code=coupon_code,
                    status="claimed",
                    claimed_at=now,
                    expires_at=expires_at,
                )
            )
            user.points = (user.points or 0) + Config.POINTS_CLAIM
            db.session.commit()

            refreshed_campaign = CampaignRepository.get(campaign_id)
            reason = cls._recommendation_reason(user, refreshed_campaign)
            return {
                "coupon_code": coupon_code,
                "reason": reason,
                "stock_left": refreshed_campaign.stock,
            }
        except ClaimError:
            raise
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def _recommendation_reason(user, campaign):
        try:
            recommendations = ai_gateway.recommend_coupons(user, [campaign])
            if recommendations:
                return recommendations[0].get("reason", "为您推荐")
        except Exception:
            pass
        return "智能推荐"
