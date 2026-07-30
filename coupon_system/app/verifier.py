"""Verifier blueprint - coupon verification/redemption."""
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from flask_login import login_required, current_user
from app import db
from app.models import Coupon, User, Campaign
from app.decorators import verifier_required
from config import Config

verifier_bp = Blueprint('verifier', __name__)


@verifier_bp.before_request
@login_required
@verifier_required
def before_request():
    pass


@verifier_bp.route('/dashboard')
def dashboard():
    """Verifier main dashboard - verification form."""
    return render_template('verifier/dashboard.html')


@verifier_bp.route('/search', methods=['POST'])
def search_coupons():
    """Search coupons by user phone number."""
    phone = request.form.get('phone', '').strip()
    if not phone:
        return jsonify({'success': False, 'message': '请输入手机号。'})

    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({'success': False, 'message': '未找到该手机号对应的用户。'})

    # Get user's claimed (not yet verified) coupons
    coupons = Coupon.query.filter_by(
        user_id=user.id,
        status='claimed'
    ).join(Campaign).order_by(Campaign.end_date.asc()).all()

    # Filter out expired coupons (check individual expiry first, then campaign)
    now = datetime.now()
    valid_coupons = []
    for c in coupons:
        expiry = c.effective_expiry
        if expiry and expiry >= now:
            valid_coupons.append(c)

    if not valid_coupons:
        return jsonify({
            'success': False,
            'message': f'用户 {user.username} 没有可核销的优惠券。',
        })

    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'coupons': [c.to_dict() for c in valid_coupons],
    })


@verifier_bp.route('/verify/<int:coupon_id>', methods=['POST'])
def verify_coupon(coupon_id):
    """Verify (redeem) a coupon - idempotent operation."""
    coupon = Coupon.query.get_or_404(coupon_id)

    # Idempotent: already verified
    if coupon.status == 'verified':
        return jsonify({
            'success': True,
            'message': '该优惠券已核销。',
            'idempotent': True,
            'verified_at': coupon.verified_at.strftime('%Y-%m-%d %H:%M:%S') if coupon.verified_at else '',
        })

    # Check if expired
    if coupon.status == 'expired':
        return jsonify({
            'success': False,
            'message': '券已过期，无法核销。',
        })

    now = datetime.now()
    expiry = coupon.effective_expiry
    if expiry and now > expiry:
        # Mark as expired
        coupon.status = 'expired'
        # Deduct points from user
        if coupon.owner:
            coupon.owner.points = max(0, coupon.owner.points + Config.POINTS_EXPIRE)
        db.session.commit()
        return jsonify({
            'success': False,
            'message': '券已过期，无法核销。积分已扣除。',
        })

    # Perform verification
    coupon.status = 'verified'
    coupon.verified_at = now
    coupon.verified_by = current_user.id

    # Award points to the coupon owner
    if coupon.owner:
        coupon.owner.points += Config.POINTS_VERIFY

    # Award points to verifier too
    current_user.points += Config.POINTS_VERIFY

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'核销成功！优惠券 {coupon.code} 已核销。',
        'verified_at': coupon.verified_at.strftime('%Y-%m-%d %H:%M:%S'),
        'coupon': coupon.to_dict(),
    })


@verifier_bp.route('/verify-by-code', methods=['POST'])
def verify_by_code():
    """Verify a coupon directly by its code string — idempotent."""
    code = request.form.get('code', '').strip().upper()
    if not code:
        return jsonify({'success': False, 'message': '请输入优惠券码。'}), 400

    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon:
        return jsonify({
            'success': False,
            'message': '券码不存在，请核对后重试。',
        }), 404

    # Idempotent: already verified
    if coupon.status == 'verified':
        return jsonify({
            'success': True,
            'idempotent': True,
            'message': f'该优惠券已核销，无需重复操作。',
            'verified_at': coupon.verified_at.strftime('%Y-%m-%d %H:%M:%S') if coupon.verified_at else '',
            'coupon': coupon.to_dict(),
        })

    # Check if expired
    if coupon.status == 'expired':
        return jsonify({
            'success': False,
            'message': '该券已过期，无法核销。',
        }), 400

    now = datetime.now()
    expiry = coupon.effective_expiry
    if expiry and now > expiry:
        coupon.status = 'expired'
        if coupon.owner:
            coupon.owner.points = max(0, coupon.owner.points + Config.POINTS_EXPIRE)
        db.session.commit()
        return jsonify({
            'success': False,
            'message': '该券已过期，无法核销。积分已扣除。',
        }), 400

    # Only 'claimed' status can be verified
    if coupon.status != 'claimed':
        return jsonify({
            'success': False,
            'message': f'该券状态异常，无法核销。',
        }), 400

    # Perform verification
    coupon.status = 'verified'
    coupon.verified_at = now
    coupon.verified_by = current_user.id

    if coupon.owner:
        coupon.owner.points += Config.POINTS_VERIFY
    current_user.points += Config.POINTS_VERIFY

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'核销成功！{coupon.code}（{coupon.campaign.name}）已核销。',
        'verified_at': coupon.verified_at.strftime('%Y-%m-%d %H:%M:%S'),
        'coupon': coupon.to_dict(),
    })


@verifier_bp.route('/history')
def history():
    """Verification history."""
    verifications = Coupon.query.filter_by(
        verified_by=current_user.id
    ).order_by(Coupon.verified_at.desc()).limit(50).all()

    return render_template('verifier/history.html', verifications=verifications)
