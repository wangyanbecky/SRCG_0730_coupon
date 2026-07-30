"""Operator routes for campaigns, risks, and notifications."""

from collections import Counter
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from api.app.extensions import db
from api.app.models import Campaign, Coupon, Notification, RiskLog, User
from api.app.security import operator_required


operator_bp = Blueprint("operator", __name__)


@operator_bp.before_request
@login_required
@operator_required
def before_request():
    pass


@operator_bp.route("/dashboard")
def dashboard():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    active_count = sum(1 for campaign in campaigns if campaign.status == "active")
    draft_count = sum(1 for campaign in campaigns if campaign.status == "draft")
    total_stock = sum(campaign.stock for campaign in campaigns)
    pending_risks = RiskLog.query.filter_by(decision="review").count()
    return render_template(
        "operator/dashboard.html",
        campaigns=campaigns,
        active_count=active_count,
        draft_count=draft_count,
        total_stock=total_stock,
        pending_risks=pending_risks,
    )


@operator_bp.route("/campaigns/create", methods=["GET", "POST"])
def create_campaign():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        amount = request.form.get("amount", "0").strip()
        stock = request.form.get("stock", "0").strip()
        start_date_str = request.form.get("start_date", "")
        end_date_str = request.form.get("end_date", "")
        per_user_limit = request.form.get("per_user_limit", "1").strip()
        coupon_validity_str = request.form.get("coupon_validity_days", "").strip()
        description = request.form.get("description", "").strip()
        is_scheduled = request.form.get("is_scheduled") == "on"
        scheduled_time_str = request.form.get("scheduled_time", "")

        errors = []
        if not name:
            errors.append("活动名称不能为空")
        try:
            amount = float(amount)
            if amount <= 0:
                errors.append("面额必须大于0")
        except ValueError:
            errors.append("面额格式不正确")
        try:
            stock = int(stock)
            if stock <= 0:
                errors.append("库存必须大于0")
        except ValueError:
            errors.append("库存格式不正确")
        try:
            per_user_limit = int(per_user_limit)
            if per_user_limit < 1:
                errors.append("每人限领数至少为1")
        except ValueError:
            errors.append("限领数格式不正确")

        coupon_validity_days = None
        if coupon_validity_str:
            try:
                coupon_validity_days = int(coupon_validity_str)
                if coupon_validity_days < 1:
                    errors.append("券有效期至少为1天")
            except ValueError:
                errors.append("券有效期格式不正确")

        if not start_date_str or not end_date_str:
            errors.append("请填写有效期")
        else:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M")
                if start_date >= end_date:
                    errors.append("结束时间必须晚于开始时间")
            except ValueError:
                errors.append("日期格式不正确")

        scheduled_time = None
        if is_scheduled and scheduled_time_str:
            try:
                scheduled_time = datetime.strptime(
                    scheduled_time_str, "%Y-%m-%dT%H:%M"
                )
            except ValueError:
                errors.append("预约时间格式不正确")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "operator/campaign_form.html", campaign=None, is_edit=False
            )

        if is_scheduled and scheduled_time:
            start_date = scheduled_time

        campaign = Campaign(
            name=name,
            amount=amount,
            stock=stock,
            initial_stock=stock,
            start_date=start_date,
            end_date=end_date,
            per_user_limit=per_user_limit,
            description=description,
            status="active",
            is_scheduled=is_scheduled,
            scheduled_time=scheduled_time,
            coupon_validity_days=coupon_validity_days,
            created_by=current_user.id,
        )
        db.session.add(campaign)
        db.session.commit()
        flash(f'活动"{name}"创建成功！', "success")
        return redirect(url_for("operator.dashboard"))

    return render_template("operator/campaign_form.html", campaign=None, is_edit=False)


@operator_bp.route("/campaigns/<int:campaign_id>/edit", methods=["GET", "POST"])
def edit_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if request.method == "POST":
        campaign.name = request.form.get("name", campaign.name).strip()
        campaign.description = request.form.get(
            "description", campaign.description
        ).strip()
        try:
            campaign.amount = float(request.form.get("amount", campaign.amount))
            new_stock = int(request.form.get("stock", campaign.stock))
            stock_diff = new_stock - campaign.stock
            campaign.stock = new_stock
            campaign.initial_stock += stock_diff
            if campaign.initial_stock < 0:
                campaign.initial_stock = 0
            campaign.per_user_limit = int(
                request.form.get("per_user_limit", campaign.per_user_limit)
            )
            validity = request.form.get("coupon_validity_days", "").strip()
            campaign.coupon_validity_days = int(validity) if validity else None
        except ValueError:
            flash("数值格式不正确。", "error")
            return render_template(
                "operator/campaign_form.html", campaign=campaign, is_edit=True
            )

        start_str = request.form.get("start_date", "")
        end_str = request.form.get("end_date", "")
        if start_str:
            campaign.start_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M")
        if end_str:
            campaign.end_date = datetime.strptime(end_str, "%Y-%m-%dT%H:%M")
        campaign.status = request.form.get("status", campaign.status)
        db.session.commit()
        flash(f'活动"{campaign.name}"更新成功！', "success")
        return redirect(url_for("operator.dashboard"))

    return render_template(
        "operator/campaign_form.html", campaign=campaign, is_edit=True
    )


@operator_bp.route("/campaigns/<int:campaign_id>/insights")
def campaign_insights(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    coupons = campaign.coupons.order_by(Coupon.claimed_at.desc()).all()
    claimed = [coupon for coupon in coupons if coupon.status == "claimed"]
    verified = [coupon for coupon in coupons if coupon.status == "verified"]
    expired = [coupon for coupon in coupons if coupon.status == "expired"]
    hour_dist = Counter()
    for coupon in coupons:
        if coupon.claimed_at:
            hour_dist[coupon.claimed_at.strftime("%m-%d %H:00")] += 1
    sorted_hours = sorted(hour_dist.items()) if hour_dist else []
    return render_template(
        "operator/insights.html",
        campaign=campaign,
        coupons=coupons,
        claimed_count=len(claimed),
        verified_count=len(verified),
        expired_count=len(expired),
        hour_distribution=sorted_hours,
    )


@operator_bp.route("/risk-logs")
def risk_logs():
    logs = RiskLog.query.order_by(RiskLog.created_at.desc()).all()
    return render_template("operator/risk_logs.html", logs=logs)


@operator_bp.route("/risk-logs/<int:log_id>/resolve", methods=["POST"])
def resolve_risk_log(log_id):
    log = RiskLog.query.get_or_404(log_id)
    action = request.form.get("action", "allow")
    log.decision = action
    log.reason = request.form.get("reason", log.reason)
    db.session.commit()
    flash(f"风险记录 #{log_id} 已处理。", "success")
    return redirect(url_for("operator.risk_logs"))


@operator_bp.route("/notifications", methods=["GET", "POST"])
def notifications():
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        target_type = request.form.get("target_type", "all")
        target_users = request.form.get("target_users", "")
        if not message:
            flash("请输入通知内容。", "error")
            return redirect(url_for("operator.notifications"))
        notification = Notification(
            message=message,
            target_type=target_type,
            target_users=target_users if target_type == "selected" else "",
            created_by=current_user.id,
        )
        db.session.add(notification)
        db.session.commit()
        flash("通知已发送！", "success")
        return redirect(url_for("operator.dashboard"))

    users = User.query.filter_by(role="user").all()
    notifications_list = (
        Notification.query.order_by(Notification.created_at.desc()).limit(20).all()
    )
    return render_template(
        "operator/notifications.html",
        users=users,
        notifications=notifications_list,
    )
