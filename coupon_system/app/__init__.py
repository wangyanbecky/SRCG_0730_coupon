"""App factory for the Coupon System."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录后再访问此页面。'


def create_app(config_class=Config):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.auth import auth_bp
    from app.operator import operator_bp
    from app.user_bp import user_bp
    from app.verifier import verifier_bp
    from app.admin_bp import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(operator_bp, url_prefix='/operator')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(verifier_bp, url_prefix='/verifier')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Import models so they are registered
    from app import models  # noqa: F401

    # Create tables and seed data
    with app.app_context():
        db.create_all()
        _seed_data()

    # Context processor for template globals
    @app.context_processor
    def inject_globals():
        from app.ai_service import ai_service
        return {
            'User': models.User,
            'Campaign': models.Campaign,
            'Coupon': models.Coupon,
            'ai_status': ai_service.status,
        }

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))


def _seed_data():
    """Create demo users and sample campaigns if the database is empty."""
    from app.models import User, Campaign, Notification
    from datetime import datetime, timedelta

    if User.query.first() is not None:
        return  # Already seeded

    # Create demo users
    users = [
        User(username='operator', role='operator', phone='13800000001',
             age=30, gender='男', hobbies='运营,数据分析', occupation='运营经理'),
        User(username='user1', role='user', phone='13800000002',
             age=25, gender='女', hobbies='购物,美食', occupation='设计师'),
        User(username='user2', role='user', phone='13800000003',
             age=28, gender='男', hobbies='运动,旅游', occupation='工程师'),
        User(username='user3', role='user', phone='13800000004',
             age=22, gender='女', hobbies='读书,音乐', occupation='学生'),
        User(username='verifier', role='verifier', phone='13800000005'),
        User(username='admin', role='admin', phone='13800000006'),
    ]
    for u in users:
        u.password = u.username + '123'
        u.last_login = datetime.now()
        db.session.add(u)
    db.session.flush()

    # Create sample campaigns
    now = datetime.now()
    campaigns = [
        Campaign(
            name='新人专享优惠券', amount=50.0, stock=100, initial_stock=100,
            start_date=now - timedelta(days=1), end_date=now + timedelta(days=30),
            per_user_limit=1, description='新用户专享，全场通用，满100减50',
            status='active', created_by=users[0].id
        ),
        Campaign(
            name='夏日清凉节', amount=30.0, stock=50, initial_stock=50,
            start_date=now - timedelta(days=7), end_date=now + timedelta(days=7),
            per_user_limit=2, description='夏季清凉商品专用券，满80减30',
            status='active', created_by=users[0].id
        ),
        Campaign(
            name='限时秒杀券', amount=100.0, stock=1, initial_stock=1,
            start_date=now, end_date=now + timedelta(hours=1),
            per_user_limit=1, description='限时秒杀，大额优惠，每人限领1张',
            status='active', created_by=users[0].id
        ),
        Campaign(
            name='会员日特惠', amount=20.0, stock=200, initial_stock=200,
            start_date=now + timedelta(days=1), end_date=now + timedelta(days=15),
            per_user_limit=3, description='会员日专属优惠券',
            status='active', is_scheduled=True,
            scheduled_time=now + timedelta(days=1),
            created_by=users[0].id
        ),
    ]
    for c in campaigns:
        db.session.add(c)
    db.session.flush()

    # Create a welcome notification
    notification = Notification(
        message='欢迎来到优惠券系统！新人专享券已上线，快来领取吧！',
        target_type='all', created_by=users[0].id
    )
    db.session.add(notification)

    db.session.commit()
    print("[OK] Database seeded with demo data.")
