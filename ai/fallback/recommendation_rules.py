"""Deterministic recommendation fallback rules."""
from __future__ import annotations

from ..contracts import Campaign, Recommendation, UserProfile


def recommend_by_rules(
    user: UserProfile, campaigns: list[Campaign]
) -> list[Recommendation]:
    """Rank by expiry, value, stock urgency, and hobby relevance."""
    recommendations: list[Recommendation] = []
    for campaign in campaigns:
        score = 0.5
        reason = "热门优惠券"
        days_left = campaign.days_left if campaign.days_left is not None else 30

        if days_left <= 1:
            score += 0.3
            reason = "即将过期，抓紧领取！"
        elif days_left <= 3:
            score += 0.2
            reason = "限时优惠，即将截止"
        elif days_left <= 7:
            score += 0.1
            reason = "近期热门，推荐领取"

        if campaign.amount >= 100:
            score += 0.15
            if "抓紧" not in reason:
                reason = "大额优惠，超值之选"
        elif campaign.amount >= 50:
            score += 0.1
            if reason == "热门优惠券":
                reason = "实惠好券，值得拥有"

        if 0 < campaign.stock <= 5:
            score += 0.15
            reason = f"仅剩{campaign.stock}张，手慢无！"
        elif 5 < campaign.stock <= 20:
            score += 0.05

        description = campaign.description.casefold()
        for hobby in user.hobbies:
            if hobby.casefold() in description:
                score += 0.1
                reason = f"适合{hobby}爱好者的专属优惠"
                break

        recommendations.append(
            Recommendation(
                campaign_id=campaign.campaign_id,
                reason=reason,
                score=round(min(max(score, 0.0), 1.0), 2),
            )
        )
    recommendations.sort(key=lambda item: item.score, reverse=True)
    return recommendations
