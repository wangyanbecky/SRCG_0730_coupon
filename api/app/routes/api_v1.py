"""Versioned JSON API for UI and external clients."""

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from api.app.extensions import db
from api.app.models import User
from api.app.security import user_required
from api.app.services.coupon_service import ClaimError, CouponService
from api.app.services.notification_service import NotificationService


api_v1_bp = Blueprint("api_v1", __name__)


def success(data=None, message="", status=200):
    return jsonify(success=True, data=data, message=message, error=None), status


def failure(message, error_type, status=400):
    return (
        jsonify(
            success=False,
            data=None,
            message=message,
            error={"type": error_type},
        ),
        status,
    )


@api_v1_bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    user = User.query.filter_by(username=username).first() if username else None
    if user is None or not password or not user.check_password(password):
        return failure("用户名或密码错误。", "invalid_credentials", 401)
    user.last_login = datetime.now()
    db.session.commit()
    login_user(user)
    return success(user.to_dict(), "登录成功")


@api_v1_bp.post("/auth/register")
def register():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return failure("用户名和密码为必填项。", "missing_credentials")
    if len(password) < 3:
        return failure("密码长度至少为3位。", "invalid_password")
    if User.query.filter_by(username=username).first() is not None:
        return failure("该用户名已被注册。", "username_exists", 409)

    age = payload.get("age")
    try:
        age = int(age) if age not in (None, "") else None
    except (TypeError, ValueError):
        return failure("年龄必须是整数。", "invalid_age")

    user = User(
        username=username,
        role="user",
        phone=str(payload.get("phone", "")).strip(),
        age=age,
        gender=str(payload.get("gender", "")).strip(),
        hobbies=str(payload.get("hobbies", "")).strip(),
        occupation=str(payload.get("occupation", "")).strip(),
        last_login=datetime.now(),
    )
    user.password = password
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return success(user.to_dict(), "注册成功", 201)


@api_v1_bp.post("/auth/logout")
@login_required
def logout():
    logout_user()
    return success(message="退出成功")


@api_v1_bp.get("/auth/me")
@login_required
def me():
    return success(current_user.to_dict())


@api_v1_bp.get("/campaigns")
@login_required
def campaigns():
    items = CouponService.list_claimable_campaigns()
    return success([campaign.to_dict() for campaign in items])


@api_v1_bp.post("/campaigns/<int:campaign_id>/claim")
@login_required
@user_required
def claim_campaign(campaign_id):
    try:
        result = CouponService.claim(campaign_id, current_user)
    except ClaimError as error:
        return failure(error.message, error.error_type, error.status_code)
    return success(result, f'领取成功！{result["reason"]}')


@api_v1_bp.get("/users/me/coupons")
@login_required
@user_required
def my_coupons():
    coupons = CouponService.list_user_coupons(current_user.id)
    return success([coupon.to_dict() for coupon in coupons])


@api_v1_bp.get("/users/me/notifications")
@login_required
@user_required
def my_notifications():
    notifications = NotificationService.visible_for_user(current_user.id)
    return success([notification.to_dict() for notification in notifications])


@api_v1_bp.get("/users/me/profile")
@login_required
@user_required
def get_profile():
    return success(current_user.to_dict())


@api_v1_bp.put("/users/me/profile")
@login_required
@user_required
def update_profile():
    payload = request.get_json(silent=True) or {}
    for field in ("phone", "gender", "hobbies", "occupation"):
        if field in payload:
            setattr(current_user, field, str(payload[field]).strip())
    if "age" in payload:
        try:
            current_user.age = int(payload["age"]) if payload["age"] is not None else None
        except (TypeError, ValueError):
            return failure("年龄必须是整数。", "invalid_age")
    db.session.commit()
    return success(current_user.to_dict(), "个人信息已更新")
