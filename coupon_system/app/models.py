"""Database models for the Coupon System."""
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # operator, user, verifier, admin
    phone = db.Column(db.String(20), default='')
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), default='')
    hobbies = db.Column(db.String(200), default='')
    occupation = db.Column(db.String(100), default='')
    points = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    coupons = db.relationship('Coupon', backref='owner', lazy='dynamic',
                              foreign_keys='Coupon.user_id')

    @property
    def password(self):
        raise AttributeError('password is not readable')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'phone': self.phone,
            'age': self.age,
            'gender': self.gender,
            'hobbies': self.hobbies,
            'occupation': self.occupation,
            'points': self.points,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M') if self.last_login else '',
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    initial_stock = db.Column(db.Integer, nullable=False, default=0)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    per_user_limit = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, active, expired, cancelled
    is_scheduled = db.Column(db.Boolean, default=False)
    scheduled_time = db.Column(db.DateTime, nullable=True)
    coupon_validity_days = db.Column(db.Integer, nullable=True)  # days coupon is valid after claim; NULL = use campaign end_date
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    creator = db.relationship('User', backref='campaigns_created', foreign_keys=[created_by])
    coupons = db.relationship('Coupon', backref='campaign', lazy='dynamic')

    @property
    def claim_rate(self):
        if self.initial_stock == 0:
            return 0.0
        claimed = self.initial_stock - self.stock
        return round(claimed / self.initial_stock * 100, 1)

    @property
    def verify_rate(self):
        if self.initial_stock == 0:
            return 0.0
        verified = self.coupons.filter_by(status='verified').count()
        return round(verified / self.initial_stock * 100, 1)

    @property
    def is_active(self):
        now = datetime.now()
        return (
            self.status == 'active'
            and self.start_date <= now <= self.end_date
            and self.stock > 0
        )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'amount': self.amount,
            'stock': self.stock,
            'initial_stock': self.initial_stock,
            'start_date': self.start_date.strftime('%Y-%m-%d %H:%M'),
            'end_date': self.end_date.strftime('%Y-%m-%d %H:%M'),
            'per_user_limit': self.per_user_limit,
            'description': self.description,
            'status': self.status,
            'claim_rate': self.claim_rate,
            'verify_rate': self.verify_rate,
            'coupon_validity_days': self.coupon_validity_days,
        }

    def __repr__(self):
        return f'<Campaign {self.name} stock={self.stock}>'


class Coupon(db.Model):
    __tablename__ = 'coupons'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='claimed')  # claimed, verified, expired
    claimed_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=True)  # individual coupon expiry; NULL = fall back to campaign.end_date
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    verifier = db.relationship('User', backref='verifications', foreign_keys=[verified_by])

    @property
    def effective_expiry(self):
        """Return the coupon's actual expiry: individual expires_at, or campaign end_date."""
        if self.expires_at:
            return self.expires_at
        if self.campaign:
            return self.campaign.end_date
        return None

    @property
    def is_expired(self):
        from datetime import datetime as dt
        expiry = self.effective_expiry
        return expiry is not None and dt.now() > expiry

    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'campaign_name': self.campaign.name if self.campaign else '',
            'user_id': self.user_id,
            'code': self.code,
            'status': self.status,
            'claimed_at': self.claimed_at.strftime('%Y-%m-%d %H:%M:%S') if self.claimed_at else '',
            'expires_at': self.expires_at.strftime('%Y-%m-%d %H:%M:%S') if self.expires_at else '',
            'verified_at': self.verified_at.strftime('%Y-%m-%d %H:%M:%S') if self.verified_at else '',
        }

    def __repr__(self):
        return f'<Coupon {self.code} ({self.status})>'


class RiskLog(db.Model):
    __tablename__ = 'risk_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    risk_score = db.Column(db.Float, default=0.0)
    decision = db.Column(db.String(20), nullable=False, default='allow')  # allow, block, review
    reason = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='risk_logs', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else '',
            'action': self.action,
            'risk_score': round(self.risk_score, 2),
            'decision': self.decision,
            'reason': self.reason,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
        }


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.String(20), nullable=False, default='all')  # all, selected
    target_users = db.Column(db.Text, default='')  # comma-separated user IDs
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    creator = db.relationship('User', backref='notifications_sent', foreign_keys=[created_by])

    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'target_type': self.target_type,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'creator': self.creator.username if self.creator else '',
        }
