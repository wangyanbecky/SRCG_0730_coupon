"""Coupon-user page routes."""

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from api.app.extensions import db
from api.app.security import user_required
from api.app.services import ai_gateway
from api.app.services.coupon_service import ClaimError, CouponService
from api.app.services.notification_service import NotificationService


user_bp = Blueprint("user_bp", __name__)


@user_bp.before_request
@login_required
@user_required
def before_request():
    pass


@user_bp.route("/dashboard")
def dashboard():
    now = datetime.now()
    active_campaigns = CouponService.list_claimable_campaigns(now)
    user_claimed_map = CouponService.claimed_counts(current_user.id, active_campaigns)

    recommendations = ai_gateway.recommend_coupons(current_user, active_campaigns)
    for recommendation in recommendations:
        campaign_id = recommendation["campaign"].id
        recommendation["is_maxed"] = (
            user_claimed_map.get(campaign_id, 0)
            >= recommendation["campaign"].per_user_limit
        )
        recommendation["user_claimed"] = user_claimed_map.get(campaign_id, 0)

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
