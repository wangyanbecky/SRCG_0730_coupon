"""Environment-backed configuration for the standalone AI package."""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Any, Mapping


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return result


@dataclass(frozen=True, slots=True)
class AIConfig:
    """AI settings. Secrets are accepted but excluded from representations."""

    region: str = "us-east-1"
    model_id: str = "deepseek.v3.2"
    bearer_token: str = field(default="", repr=False)
    mock_mode: bool = True
    converse_timeout: int = 60
    list_models_timeout: int = 10
    max_tokens: int = 1024
    risk_claim_window_seconds: int = 10
    risk_max_claims_in_window: int = 50

    def __post_init__(self) -> None:
        if not self.region.strip():
            raise ValueError("region must not be empty")
        if not self.model_id.strip():
            raise ValueError("model_id must not be empty")
        for name in (
            "converse_timeout",
            "list_models_timeout",
            "max_tokens",
            "risk_claim_window_seconds",
            "risk_max_claims_in_window",
        ):
            _as_int(getattr(self, name), name)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "AIConfig":
        """Build configuration without loading a .env file or exposing values."""
        env = os.environ if environ is None else environ
        return cls(
            region=env.get("AWS_REGION", "us-east-1"),
            model_id=env.get("BEDROCK_MODEL_ID", "deepseek.v3.2"),
            bearer_token=env.get("AWS_BEARER_TOKEN_BEDROCK", ""),
            mock_mode=_as_bool(env.get("AI_MOCK_MODE", "true")),
            converse_timeout=_as_int(
                env.get("BEDROCK_CONVERSE_TIMEOUT", 60),
                "BEDROCK_CONVERSE_TIMEOUT",
            ),
            list_models_timeout=_as_int(
                env.get("BEDROCK_LIST_MODELS_TIMEOUT", 10),
                "BEDROCK_LIST_MODELS_TIMEOUT",
            ),
            max_tokens=_as_int(env.get("BEDROCK_MAX_TOKENS", 1024), "BEDROCK_MAX_TOKENS"),
            risk_claim_window_seconds=_as_int(
                env.get("RISK_CLAIM_WINDOW_SECONDS", 10),
                "RISK_CLAIM_WINDOW_SECONDS",
            ),
            risk_max_claims_in_window=_as_int(
                env.get("RISK_MAX_CLAIMS_IN_WINDOW", 50),
                "RISK_MAX_CLAIMS_IN_WINDOW",
            ),
        )

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "AIConfig":
        """Build from caller-provided field names or compatible env names."""
        aliases = {
            "AWS_REGION": "region",
            "BEDROCK_MODEL_ID": "model_id",
            "AWS_BEARER_TOKEN_BEDROCK": "bearer_token",
            "AI_MOCK_MODE": "mock_mode",
            "BEDROCK_CONVERSE_TIMEOUT": "converse_timeout",
            "BEDROCK_LIST_MODELS_TIMEOUT": "list_models_timeout",
            "BEDROCK_MAX_TOKENS": "max_tokens",
            "RISK_CLAIM_WINDOW_SECONDS": "risk_claim_window_seconds",
            "RISK_MAX_CLAIMS_IN_WINDOW": "risk_max_claims_in_window",
        }
        valid_names = {item.name for item in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in values.items():
            name = aliases.get(key, key)
            if name in valid_names:
                kwargs[name] = value
        if "mock_mode" in kwargs:
            kwargs["mock_mode"] = _as_bool(kwargs["mock_mode"])
        for name in (
            "converse_timeout",
            "list_models_timeout",
            "max_tokens",
            "risk_claim_window_seconds",
            "risk_max_claims_in_window",
        ):
            if name in kwargs:
                kwargs[name] = _as_int(kwargs[name], name)
        return cls(**kwargs)
