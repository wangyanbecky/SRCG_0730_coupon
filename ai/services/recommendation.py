"""Coupon recommendation orchestration with automatic rule fallback."""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from ..contracts import Campaign, Recommendation, UserProfile
from ..fallback.recommendation_rules import recommend_by_rules
from ..prompts.recommendation import build_recommendation_prompt
from ..providers.base import TextProvider


def _json_object(text: str) -> Mapping[str, Any]:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    candidate = match.group(1) if match else text
    value = json.loads(candidate.strip())
    if not isinstance(value, Mapping):
        raise ValueError("provider response must be a JSON object")
    return value


class RecommendationService:
    def __init__(self, provider: TextProvider) -> None:
        self.provider = provider

    def recommend(
        self,
        user_profile: UserProfile | Mapping[str, Any],
        campaigns: Sequence[Campaign | Mapping[str, Any]],
    ) -> list[Recommendation]:
        user = (
            user_profile
            if isinstance(user_profile, UserProfile)
            else UserProfile.from_mapping(user_profile)
        )
        campaign_list = [
            item if isinstance(item, Campaign) else Campaign.from_mapping(item)
            for item in campaigns
        ]
        if not campaign_list:
            return []
        if not self.provider.available:
            return recommend_by_rules(user, campaign_list)
        try:
            text = self.provider.converse(
                [{"role": "user", "content": build_recommendation_prompt(user, campaign_list)}]
            )
            result = self._parse_recommendations(text, campaign_list)
            return result or recommend_by_rules(user, campaign_list)
        except Exception:
            return recommend_by_rules(user, campaign_list)

    @staticmethod
    def _parse_recommendations(
        text: str, campaigns: list[Campaign]
    ) -> list[Recommendation]:
        payload = _json_object(text)
        items = payload.get("recommendations")
        if not isinstance(items, list):
            raise ValueError("recommendations must be a list")
        campaign_ids = {str(item.campaign_id): item.campaign_id for item in campaigns}
        recommendations: list[Recommendation] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, Mapping):
                continue
            key = str(item.get("campaign_id"))
            if key not in campaign_ids or key in seen:
                continue
            score = min(max(float(item.get("score", 0.5)), 0.0), 1.0)
            reason = str(item.get("reason") or "为您精选推荐")
            recommendations.append(
                Recommendation(campaign_ids[key], reason, round(score, 2))
            )
            seen.add(key)
        recommendations.sort(key=lambda item: item.score, reverse=True)
        return recommendations
