"""Coupon-user page routes."""

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from api.app.extensions import db
from api.app.security import user_required
from api.app.services import ai_gateway
from api.app.services.coupon_service import ClaimError, CouponService
from api.app.services.notification_service import NotificationService
from api.app.services.reservation_service import ReservationError, ReservationService


user_bp = Blueprint("user_bp", __name__)


@user_bp.before_request
@login_required
@user_required
def before_request():
    pass


@user_bp.route("/dashboard")
def dashboard():
    now = datetime.now()
    visible_campaigns = CouponService.list_user_visible_campaigns(now)
    user_claimed_map = CouponService.claimed_counts(
        current_user.id,
        visible_campaigns,
    )
    reserved_campaign_ids = ReservationService.campaign_ids_for_user(current_user.id)

    recommendations = ai_gateway.recommend_coupons(current_user, visible_campaigns)
    recommended_ids = {
        recommendation["campaign"].id for recommendation in recommendations
    }
    for campaign in visible_campaigns:
        if campaign.id not in recommended_ids:
            recommendations.append(
                {
                    "campaign": campaign,
                    "reason": "即将开始，先预约收藏" if campaign.is_pending_release_at(now) else "为您精选推荐",
                    "score": 0.5,
                }
            )

    for recommendation in recommendations:
        campaign = recommendation["campaign"]
        campaign_id = campaign.id
        recommendation["is_maxed"] = (
            user_claimed_map.get(campaign_id, 0) >= campaign.per_user_limit
        )
        recommendation["user_claimed"] = user_claimed_map.get(campaign_id, 0)
        recommendation["is_pending"] = campaign.is_pending_release_at(now)
        recommendation["is_reserved"] = campaign_id in reserved_campaign_ids

    ai_picks = [item for item in recommendations if item["score"] >= 0.6]
    ai_pick_ids = {item["campaign"].id for item in ai_picks}
    other_campaigns = [
        item for item in recommendations if item["campaign"].id not in ai_pick_ids
    ]
    return render_template(
        "user/dashboard.html",
        ai_picks=ai_picks,
        other_campaigns=other_campaigns,
        broadcasts=NotificationService.visible_for_user(current_user.id),
        near_expiry=CouponService.near_expiry(current_user.id, now),
        now=now,
    )


@user_bp.route("/claim/<int:campaign_id>", methods=["POST"])
def claim_coupon(campaign_id):
    try:
        result = CouponService.claim(campaign_id, current_user)
    except ClaimError as error:
        return jsonify(error.to_dict()), error.status_code
    return jsonify(
        success=True,
        message=f'领取成功！{result["reason"]}',
        **result,
    )


@user_bp.route("/reserve/<int:campaign_id>", methods=["POST"])
def reserve_campaign(campaign_id):
    try:
        result = ReservationService.reserve(campaign_id, current_user.id)
    except ReservationError as error:
        return jsonify(error.to_dict()), error.status_code
    message = "预约成功，已为您收藏。" if result["created"] else "您已预约过该活动。"
    return jsonify(
        success=True,
        message=message,
        reserved=True,
        already_reserved=not result["created"],
    )


@user_bp.route("/my-coupons")
def my_coupons():
    return render_template(
        "user/my_coupons.html",
        coupons=CouponService.list_user_coupons(current_user.id),
    )


@user_bp.route("/profile", methods=["GET", "POST"])
def profile():
    if request.method == "POST":
        current_user.phone = request.form.get("phone", current_user.phone).strip()
        current_user.gender = request.form.get("gender", current_user.gender).strip()
        current_user.hobbies = request.form.get("hobbies", current_user.hobbies).strip()
        current_user.occupation = request.form.get(
            "occupation", current_user.occupation
        ).strip()
        age_str = request.form.get("age", "").strip()
        if age_str:
            try:
                current_user.age = int(age_str)
            except ValueError:
                pass
        db.session.commit()
        flash("个人信息已更新。", "success")
        return redirect(url_for("user_bp.profile"))
    return render_template("user/profile.html")
