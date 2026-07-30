"""Integration coverage for the highest-risk coupon flows."""

import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from api.app import create_app
from api.app.extensions import db
from api.app.models import Campaign, Coupon, Notification, User
from api.app.services.coupon_service import CouponService
from api.config import Config


class CouponFlowTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"

        class TestConfig(Config):
            TESTING = True
            SECRET_KEY = "integration-test-secret"
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            SQLALCHEMY_ENGINE_OPTIONS = {
                "connect_args": {"timeout": 15},
            }

        self.app = create_app(TestConfig)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp_dir.cleanup()

    @staticmethod
    def _login(client, username):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": f"{username}123"},
        )
        if response.status_code != 200:
            raise AssertionError(response.get_json())

    def test_atomic_stock_allows_only_one_claim(self):
        with self.app.app_context():
            campaign = Campaign.query.filter_by(name="限时秒杀券").one()
            campaign_id = campaign.id

        barrier = threading.Barrier(3)
        results = []
        result_lock = threading.Lock()

        def claim(username):
            client = self.app.test_client()
            self._login(client, username)
            barrier.wait(timeout=5)
            response = client.post(f"/api/v1/campaigns/{campaign_id}/claim")
            with result_lock:
                results.append((response.status_code, response.get_json()))

        threads = [
            threading.Thread(target=claim, args=(username,))
            for username in ("user1", "user2", "user3")
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(3, len(results))
        self.assertEqual(1, sum(status == 200 for status, _ in results))
        self.assertEqual(
            2,
            sum(
                status == 400 and body["error"]["type"] == "out_of_stock"
                for status, body in results
            ),
        )
        with self.app.app_context():
            campaign = db.session.get(Campaign, campaign_id)
            self.assertEqual(0, campaign.stock)
            self.assertEqual(1, Coupon.query.filter_by(campaign_id=campaign_id).count())

    def test_risk_threshold_blocks_the_threshold_request(self):
        original_threshold = Config.RISK_MAX_CLAIMS_IN_WINDOW
        Config.RISK_MAX_CLAIMS_IN_WINDOW = 2
        try:
            client = self.app.test_client()
            self._login(client, "user1")
            with self.app.app_context():
                campaign_id = Campaign.query.filter_by(name="夏日清凉节").one().id

            first = client.post(f"/api/v1/campaigns/{campaign_id}/claim")
            second = client.post(f"/api/v1/campaigns/{campaign_id}/claim")

            self.assertEqual(200, first.status_code)
            self.assertEqual(403, second.status_code)
            self.assertEqual("risk_blocked", second.get_json()["error"]["type"])
        finally:
            Config.RISK_MAX_CLAIMS_IN_WINDOW = original_threshold

    def test_selected_notifications_are_visible_only_to_targets(self):
        with self.app.app_context():
            operator = User.query.filter_by(username="operator").one()
            user1 = User.query.filter_by(username="user1").one()
            user2 = User.query.filter_by(username="user2").one()
            user1_id = user1.id
            db.session.add_all(
                [
                    Notification(
                        message="仅用户1可见",
                        target_type="selected",
                        target_users=str(user1.id),
                        created_by=operator.id,
                    ),
                    Notification(
                        message="仅用户2可见",
                        target_type="selected",
                        target_users=str(user2.id),
                        created_by=operator.id,
                    ),
                ]
            )
            db.session.commit()

        client = self.app.test_client()
        self._login(client, "user1")
        response = client.get("/api/v1/users/me/notifications")
        messages = [item["message"] for item in response.get_json()["data"]]

        self.assertIn("仅用户1可见", messages)
        self.assertNotIn("仅用户2可见", messages)
        with self.app.app_context():
            self.assertEqual(
                user1_id,
                User.query.filter_by(username="user1").one().id,
            )

    def test_near_expiry_uses_coupon_effective_expiry(self):
        now = datetime.now()
        with self.app.app_context():
            user = User.query.filter_by(username="user1").one()
            campaign = Campaign.query.filter_by(name="新人专享优惠券").one()
            campaign.end_date = now + timedelta(days=30)
            near_coupon = Coupon(
                campaign_id=campaign.id,
                user_id=user.id,
                code="NEAR-EXPIRY",
                status="claimed",
                claimed_at=now,
                expires_at=now + timedelta(days=2),
            )
            later_coupon = Coupon(
                campaign_id=campaign.id,
                user_id=user.id,
                code="LATER-EXPIRY",
                status="claimed",
                claimed_at=now,
                expires_at=now + timedelta(days=5),
            )
            db.session.add_all([near_coupon, later_coupon])
            db.session.commit()

            result = CouponService.near_expiry(user.id, now=now, days=3)
            self.assertEqual(["NEAR-EXPIRY"], [coupon.code for coupon in result])


if __name__ == "__main__":
    unittest.main()
