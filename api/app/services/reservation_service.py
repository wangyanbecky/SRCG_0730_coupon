"""Business rules for reserving future coupon campaigns."""

from datetime import datetime

from api.app.repositories import CampaignRepository, ReservationRepository


class ReservationError(Exception):
    def __init__(self, message, error_type, status_code=400):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code

    def to_dict(self):
        return {
            "success": False,
            "message": self.message,
            "error_type": self.error_type,
        }


class ReservationService:
    @staticmethod
    def campaign_ids_for_user(user_id):
        return ReservationRepository.campaign_ids_for_user(user_id)

    @staticmethod
    def reserve(campaign_id, user_id, now=None):
        now = now or datetime.now()
        campaign = CampaignRepository.get(campaign_id)
        if campaign is None:
            raise ReservationError("活动不存在。", "not_found", 404)
        if not campaign.is_pending_release_at(now):
            raise ReservationError(
                "该活动已开始或当前不可预约。",
                "campaign_not_reservable",
            )
        if campaign.stock <= 0:
            raise ReservationError("优惠券已无库存。", "out_of_stock")

        reservation, created = ReservationRepository.add_idempotent(
            user_id,
            campaign_id,
        )
        return {
            "reservation_id": reservation.id,
            "created": created,
        }
