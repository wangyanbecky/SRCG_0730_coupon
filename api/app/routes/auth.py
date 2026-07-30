"""Authentication routes."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from api.app.extensions import db
from api.app.models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    role_redirects = {
        "operator": "operator.dashboard",
        "user": "user_bp.dashboard",
        "verifier": "verifier.dashboard",
        "admin": "admin_bp.dashboard",
    }
    endpoint = role_redirects.get(current_user.role)
    if endpoint:
        return redirect(url_for(endpoint))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("请输入用户名和密码。", "error")
            return render_template("login.html")

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("用户名或密码错误。", "error")
            return render_template("login.html")

        if user.role == "user" and user.last_login:
            days_inactive = (datetime.now() - user.last_login).days
            if days_inactive >= 7:
                penalty = (days_inactive // 7) * 3
                user.points = max(0, user.points - penalty)
                if penalty > 0:
                    flash(
                        f"您已 {days_inactive} 天未登录，扣除 {penalty} 积分。",
                        "warning",
                    )

        user.last_login = datetime.now()
        db.session.commit()
        login_user(user)
        flash(f"欢迎回来，{user.username}！", "success")
        return redirect(url_for("auth.index"))

    users = User.query.all()
    return render_template("login.html", users=users)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("您已成功退出登录。", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        hobbies = request.form.get("hobbies", "").strip()
        occupation = request.form.get("occupation", "").strip()

        if not username or not password:
            flash("用户名和密码为必填项。", "error")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash("该用户名已被注册。", "error")
            return render_template("register.html")
        if len(password) < 3:
            flash("密码长度至少为3位。", "error")
            return render_template("register.html")

        user = User(
            username=username,
            role="user",
            phone=phone or "",
            age=int(age) if age else None,
            gender=gender,
            hobbies=hobbies,
            occupation=occupation,
            last_login=datetime.now(),
        )
        user.password = password
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("注册成功！欢迎加入优惠券系统。", "success")
        return redirect(url_for("user_bp.dashboard"))

    return render_template("register.html")
