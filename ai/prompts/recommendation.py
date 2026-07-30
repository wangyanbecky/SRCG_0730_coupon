"""Prompt construction for coupon recommendations."""
from __future__ import annotations

import json

from ..contracts import Campaign, UserProfile


def build_recommendation_prompt(
    user: UserProfile, campaigns: list[Campaign]
) -> str:
    user_json = json.dumps(user.to_prompt_dict(), ensure_ascii=False)
    campaign_json = json.dumps(
        [campaign.to_prompt_dict() for campaign in campaigns],
        ensure_ascii=False,
        indent=2,
    )
    return (
        "You are a coupon recommendation engine. Rank the coupons using the "
        "user profile. Give each coupon a brief personalized Chinese reason "
        "and a relevance score from 0.0 to 1.0.\n\n"
        f"User profile: {user_json}\n"
        f"Available coupons: {campaign_json}\n\n"
        "Return ONLY valid JSON in this exact shape:\n"
        '{"recommendations":[{"campaign_id":1,"reason":"推荐理由",'
        '"score":0.95}]}'
    )
