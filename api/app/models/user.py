"""User model."""

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from api.app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    phone = db.Column(db.String(20), default="")
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), default="")
    hobbies = db.Column(db.String(200), default="")
    occupation = db.Column(db.String(100), default="")
    points = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)

    coupons = db.relationship(
        "Coupon", backref="owner", lazy="dynamic", foreign_keys="Coupon.user_id"
    )

    @property
    def password(self):
        raise AttributeError("password is not readable")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "phone": self.phone,
            "age": self.age,
            "gender": self.gender,
            "hobbies": self.hobbies,
            "occupation": self.occupation,
            "points": self.points,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M") if self.last_login else "",
        }

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
