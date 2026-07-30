"""Deterministic fallback engines."""

from .recommendation_rules import recommend_by_rules
from .risk_rules import assess_by_rules

__all__ = ["assess_by_rules", "recommend_by_rules"]
