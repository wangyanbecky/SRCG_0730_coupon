"""User blueprint - coupon claiming, viewing, profile."""
import uuid
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from flask_login import login_required, current_user
from app import db
from sqlalchemy import or_
from app.models import Campaign, Coupon, RiskLog, Notification
from app.ai_service import ai_service
from app.decorators import user_required
from config import Config

user_bp = Blueprint('user_bp', __name__)


@user_bp.before_request
@login_required
@user_required
def before_request():
    pass


@user_bp.route('/dashboard')
def dashboard():
    """User main dashboard with AI-ranked campaigns and broadcasts."""
    # Get available campaigns user hasn't max-claimed.
    # Include both active campaigns and draft campaigns whose scheduled_time
    # has passed (backward compatibility with campaigns created before the
    # "always active" fix in operator.create_campaign).
    now = datetime.now()
    active_campaigns = Campaign.query.filter(
        Campaign.start_date <= now,
        Campaign.end_date >= now,
    ).filter(
        or_(
            Campaign.status == 'active',
            Campaign.is_scheduled.is_(True) & (Campaign.scheduled_time <= now),
        )
    ).all()

    # Build claimed-count map for all active campaigns (for exhausted-card UI)
    user_claimed_map = {}
    for c in active_campaigns:
        user_claimed_map[c.id] = Coupon.query.filter_by(
            campaign_id=c.id, user_id=current_user.id
        ).count()

    # Get AI-ranked recommendations (all active campaigns, regardless of per-user limit)
    recommendations = ai_service.recommend_coupons(current_user, active_campaigns)
    # Attach is_maxed to each recommendation
    for r in recommendations:
        cid = r['campaign'].id
        r['is_maxed'] = user_claimed_map.get(cid, 0) >= r['campaign'].per_user_limit
        r['user_claimed'] = user_claimed_map.get(cid, 0)

    # Split: top AI picks (score >= 0.6) and the rest
    ai_picks = [r for r in recommendations if r['score'] >= 0.6]
    # Remaining campaigns — show without AI reason panel
    ai_pick_ids = {r['campaign'].id for r in ai_picks}
    other_campaigns = [r for r in recommendations if r['campaign'].id not in ai_pick_ids]

    # Get broadcasts
    broadcasts = Notification.query.order_by(
        Notification.created_at.desc()).limit(10).all()

    # Get near-expiry coupons for this user
    near_expiry_coupons = Coupon.query.filter(
        Coupon.user_id == current_user.id,
        Coupon.status == 'claimed',
    ).join(Campaign).filter(
        Campaign.end_date <= now.replace(hour=23, minute=59, second=59),
    ).all()

    # Actually check which are expiring within 3 days
    from datetime import timedelta
    threshold = now + timedelta(days=3)
    near_expiry = []
    for c in near_expiry_coupons:
        if c.campaign and c.campaign.end_date <= threshold:
            near_expiry.append(c)

    return render_template('user/dashboard.html',
                         ai_picks=ai_picks,
                         other_campaigns=other_campaigns,
                         broadcasts=broadcasts,
                         near_expiry=near_expiry,
                         now=now)


@user_bp.route('/claim/<int:campaign_id>', methods=['POST'])
def claim_coupon(campaign_id):
    """Claim a coupon with atomic inventory deduction and risk assessment."""
    campaign = Campaign.query.with_for_update().get_or_404(campaign_id)

    # Validate campaign is active
    now = datetime.now()
    if campaign.status != 'active':
        return jsonify({'success': False, 'message': '该活动未开放领取。'}), 400
    if now < campaign.start_date:
        return jsonify({'success': False, 'message': '该活动尚未开始。'}), 400
    if now > campaign.end_date:
        return jsonify({'success': False, 'message': '该活动已结束。'}), 400

    # Risk assessment
    risk = ai_service.assess_risk(current_user, 'claim_coupon')
    risk_log = RiskLog(
        user_id=current_user.id,
        action='claim_coupon',
        risk_score=risk['risk_score'],
        decision=risk['decision'],
        reason=risk['reason'],
    )
    db.session.add(risk_log)

    if risk['decision'] == 'block':
        db.session.commit()
        return jsonify({
            'success': False,
            'message': f'操作被拦截：{risk["reason"]}',
            'error_type': 'risk_blocked',
            'risk_blocked': True,
        }), 403

    # Flush risk log to DB so it persists even if eligibility checks fail/rollback
    db.session.flush()

    # Check per-user limit
    user_claimed = Coupon.query.filter_by(
        campaign_id=campaign_id, user_id=current_user.id
    ).count()

    if user_claimed >= campaign.per_user_limit:
        db.session.commit()
        return jsonify({
            'success': False,
            'message': '您已达到该活动的领取上限。',
            'error_type': 'limit_exceeded',
        }), 400

    # Atomic inventory check
    if campaign.stock <= 0:
        db.session.commit()
        return jsonify({
            'success': False,
            'message': '优惠券已被抢光！',
            'error_type': 'out_of_stock',
        }), 400

    # Deduct inventory and create coupon
    campaign.stock -= 1

    coupon_code = f"CPN-{uuid.uuid4().hex[:8].upper()}"

    # Calculate individual coupon expiry
    from datetime import timedelta as dt_timedelta
    expires_at = None
    if campaign.coupon_validity_days:
        expires_at = now + dt_timedelta(days=campaign.coupon_validity_days)

    coupon = Coupon(
        campaign_id=campaign_id,
        user_id=current_user.id,
        code=coupon_code,
        status='claimed',
        claimed_at=now,
        expires_at=expires_at,
    )
    db.session.add(coupon)

    # Award points
    current_user.points += Config.POINTS_CLAIM

    # Get AI recommendation reason for this campaign
    reason = ''
    try:
        recommendations = ai_service.recommend_coupons(current_user, [campaign])
        if recommendations:
            reason = recommendations[0].get('reason', '为您推荐')
    except Exception:
        reason = '智能推荐'

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'领取成功！{reason}',
        'coupon_code': coupon_code,
        'reason': reason,
        'stock_left': campaign.stock,
    })


@user_bp.route('/my-coupons')
def my_coupons():
    """View user's claimed and verified coupons."""
    coupons = Coupon.query.filter_by(user_id=current_user.id).order_by(
        Coupon.claimed_at.desc()
    ).all()

    return render_template('user/my_coupons.html', coupons=coupons)


@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """View and edit user profile."""
    if request.method == 'POST':
        current_user.phone = request.form.get('phone', current_user.phone).strip()
        current_user.gender = request.form.get('gender', current_user.gender).strip()
        current_user.hobbies = request.form.get('hobbies', current_user.hobbies).strip()
        current_user.occupation = request.form.get('occupation', current_user.occupation).strip()

        age_str = request.form.get('age', '').strip()
        if age_str:
            try:
                current_user.age = int(age_str)
            except ValueError:
                pass

        db.session.commit()
        flash('个人信息已更新。', 'success')
        return redirect(url_for('user_bp.profile'))

    return render_template('user/profile.html')
