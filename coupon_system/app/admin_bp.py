"""Admin dashboard and monitoring routes."""
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from app import db
from app.decorators import admin_required
from app.models import Campaign, Coupon, RiskLog, User

admin_bp = Blueprint('admin_bp', __name__)


@admin_bp.before_request
@login_required
@admin_required
def before_request():
    pass


@admin_bp.route('/dashboard')
def dashboard():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    users = User.query.filter_by(role='user').order_by(User.created_at.desc()).all()
    risk_logs = RiskLog.query.order_by(RiskLog.created_at.desc()).limit(12).all()
    total_claimed = Coupon.query.count()
    total_verified = Coupon.query.filter_by(status='verified').count()
    total_expired = Coupon.query.filter_by(status='expired').count()
    total_stock = sum(c.stock for c in campaigns)
    initial_stock = sum(c.initial_stock for c in campaigns)
    return render_template(
        'admin/dashboard.html',
        campaigns=campaigns,
        users=users,
        risk_logs=risk_logs,
        total_claimed=total_claimed,
        total_verified=total_verified,
        total_expired=total_expired,
        total_stock=total_stock,
        initial_stock=initial_stock,
    )
