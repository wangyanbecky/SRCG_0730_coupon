"""Administration dashboard and system monitoring routes."""

from flask import Blueprint, current_app, render_template, request
from flask_login import login_required

from api.app.models import Campaign, Coupon, RiskLog, User
from api.app.observability import collect_system_health, read_system_logs
from api.app.security import admin_required


admin_bp = Blueprint("admin_bp", __name__)
_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


@admin_bp.before_request
@login_required
@admin_required
def before_request():
    pass


@admin_bp.route("/dashboard")
def dashboard():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    users = User.query.filter_by(role="user").order_by(User.created_at.desc()).all()
    risk_logs = RiskLog.query.order_by(RiskLog.created_at.desc()).limit(12).all()
    total_claimed = Coupon.query.count()
    total_verified = Coupon.query.filter_by(status="verified").count()
    total_expired = Coupon.query.filter_by(status="expired").count()
    total_stock = sum(campaign.stock for campaign in campaigns)
    initial_stock = sum(campaign.initial_stock for campaign in campaigns)
    return render_template(
        "admin/dashboard.html",
        campaigns=campaigns,
        users=users,
        risk_logs=risk_logs,
        total_claimed=total_claimed,
        total_verified=total_verified,
        total_expired=total_expired,
        total_stock=total_stock,
        initial_stock=initial_stock,
    )


@admin_bp.get("/system/logs")
def system_logs():
    level = request.args.get("level", "").upper()
    if level not in _LOG_LEVELS:
        level = ""
    query = request.args.get("q", "").strip()[:100]
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50
    max_limit = current_app.config["APP_LOG_VIEW_MAX_LIMIT"]
    limit = max(1, min(limit, max_limit))
    limit_options = sorted(
        {value for value in (25, 50, 100, limit, max_limit) if value <= max_limit}
    )
    entries, log_error = read_system_logs(
        current_app,
        level=level,
        query=query,
        limit=limit,
    )
    return render_template(
        "admin/system_logs.html",
        entries=entries,
        log_error=log_error,
        selected_level=level,
        query=query,
        limit=limit,
        limit_options=limit_options,
        log_levels=_LOG_LEVELS,
    )


@admin_bp.get("/system/health")
def system_health():
    return render_template(
        "admin/system_health.html",
        health=collect_system_health(current_app),
    )


@admin_bp.get("/system/alerts")
def system_alerts():
    return render_template("admin/alerting_placeholder.html")
