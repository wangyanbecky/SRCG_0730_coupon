"""Flask application factory."""

from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, request, url_for

from api.app.extensions import db, login_manager
from api.config import Config, STATIC_DIR, TEMPLATE_DIR


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR.resolve()),
        static_folder=str(STATIC_DIR.resolve()),
    )
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/v1/"):
            return (
                jsonify(
                    success=False,
                    data=None,
                    message="请先登录。",
                    error={"type": "authentication_required"},
                ),
                401,
            )
        return redirect(url_for("auth.login"))

    @app.errorhandler(403)
    def forbidden(_error):
        if request.path.startswith("/api/v1/"):
            return (
                jsonify(
                    success=False,
                    data=None,
                    message="无权执行此操作。",
                    error={"type": "forbidden"},
                ),
                403,
            )
        return _error

    from api.app.routes import (
        admin_bp,
        api_v1_bp,
        auth_bp,
        operator_bp,
        user_bp,
        verifier_bp,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")
    app.register_blueprint(operator_bp, url_prefix="/operator")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(verifier_bp, url_prefix="/verifier")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from api.app import models

    @app.get("/api/v1/health")
    def health():
        from api.app.services import ai_gateway

        return jsonify(
            success=True,
            service="coupon-system-api",
            ai_status=ai_gateway.status,
        )

    with app.app_context():
        db.create_all()
        _seed_data()

    @app.context_processor
    def inject_globals():
        from api.app.services import ai_gateway

        return {
            "User": models.User,
            "Campaign": models.Campaign,
            "Coupon": models.Coupon,
            "ai_status": ai_gateway.status,
        }

    return app


@login_manager.user_loader
def load_user(user_id):
    from api.app.models import User

    return db.session.get(User, int(user_id))


def _seed_data():
    from api.app.models import Campaign, Notification, User

    if User.query.first() is not None:
        return

    users = [
        User(
            username="operator",
            role="operator",
            phone="13800000001",
            age=30,
            gender="男",
            hobbies="运营,数据分析",
            occupation="运营经理",
        ),
        User(
            username="user1",
            role="user",
            phone="13800000002",
            age=25,
            gender="女",
            hobbies="购物,美食",
            occupation="设计师",
        ),
        User(
            username="user2",
            role="user",
            phone="13800000003",
            age=28,
            gender="男",
            hobbies="运动,旅游",
            occupation="工程师",
        ),
        User(
            username="user3",
            role="user",
            phone="13800000004",
            age=22,
            gender="女",
            hobbies="读书,音乐",
            occupation="学生",
        ),
        User(username="verifier", role="verifier", phone="13800000005"),
        User(username="admin", role="admin", phone="13800000006"),
    ]
    for user in users:
        user.password = user.username + "123"
        user.last_login = datetime.now()
        db.session.add(user)
    db.session.flush()

    now = datetime.now()
    campaigns = [
        Campaign(
            name="新人专享优惠券",
            amount=50.0,
            stock=100,
            initial_stock=100,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            per_user_limit=1,
            description="新用户专享，全场通用，满100减50",
            status="active",
            created_by=users[0].id,
        ),
        Campaign(
            name="夏日清凉节",
            amount=30.0,
            stock=50,
            initial_stock=50,
            start_date=now - timedelta(days=7),
            end_date=now + timedelta(days=7),
            per_user_limit=2,
            description="夏季清凉商品专用券，满80减30",
            status="active",
            created_by=users[0].id,
        ),
        Campaign(
            name="限时秒杀券",
            amount=100.0,
            stock=1,
            initial_stock=1,
            start_date=now,
            end_date=now + timedelta(hours=1),
            per_user_limit=1,
            description="限时秒杀，大额优惠，每人限领1张",
            status="active",
            created_by=users[0].id,
        ),
        Campaign(
            name="会员日特惠",
            amount=20.0,
            stock=200,
            initial_stock=200,
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=15),
            per_user_limit=3,
            description="会员日专属优惠券",
            status="active",
            is_scheduled=True,
            scheduled_time=now + timedelta(days=1),
            created_by=users[0].id,
        ),
    ]
    for campaign in campaigns:
        db.session.add(campaign)
    db.session.flush()

    db.session.add(
        Notification(
            message="欢迎来到优惠券系统！新人专享券已上线，快来领取吧！",
            target_type="all",
            created_by=users[0].id,
        )
    )
    db.session.commit()
    print("[OK] Database seeded with demo data.")
