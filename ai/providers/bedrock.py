"""Amazon Bedrock provider with Bearer Token and boto3 SDK paths."""
from __future__ import annotations

import concurrent.futures
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping, Sequence

from ..config import AIConfig
from .base import (
    ProviderAccessError,
    ProviderAuthenticationError,
    ProviderContextLimitError,
    ProviderError,
    ProviderModelError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    TextProvider,
)


class BedrockProvider(TextProvider):
    """Bedrock Converse provider. A configured Bearer Token always wins over SDK."""

    def __init__(
        self,
        config: AIConfig,
        *,
        runtime_client: Any | None = None,
        model_client: Any | None = None,
        urlopen: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config
        self._runtime_client = runtime_client
        self._model_client = model_client
        self._urlopen = urlopen or urllib.request.urlopen
        self._sdk_initialization_failed = False
        if not config.bearer_token and not config.mock_mode and runtime_client is None:
            self._initialize_runtime_client()

    def _initialize_runtime_client(self) -> None:
        try:
            import boto3

            self._runtime_client = boto3.client(
                "bedrock-runtime", region_name=self.config.region
            )
        except Exception:
            self._sdk_initialization_failed = True
            self._runtime_client = None

    @property
    def available(self) -> bool:
        if self.config.mock_mode:
            return False
        return bool(self.config.bearer_token or self._runtime_client is not None)

    @property
    def status(self) -> Mapping[str, Any]:
        if self.config.mock_mode:
            mode, label = "fallback", "规则引擎降级"
        elif self.config.bearer_token:
            mode, label = "bedrock_api", "Bedrock API"
        elif self._runtime_client is not None:
            mode, label = "bedrock_sdk", "Bedrock SDK"
        else:
            mode, label = "fallback", "规则引擎降级"
        return {
            "mode": mode,
            "label": label,
            "connected": self.available,
            "model": self.config.model_id,
            "region": self.config.region,
        }

    def converse(
        self,
        messages: Sequence[Mapping[str, Any]],
        max_tokens: int | None = None,
    ) -> str:
        if not self.available:
            raise ProviderError("Bedrock is not available")
        normalized = self._normalize_messages(messages)
        token_limit = max_tokens or self.config.max_tokens
        if self.config.bearer_token:
            response = self._converse_with_bearer(normalized, token_limit)
        else:
            response = self._converse_with_sdk(normalized, token_limit)
        return self._parse_converse_response(response)

    def _converse_with_bearer(
        self, messages: list[dict[str, Any]], max_tokens: int
    ) -> Mapping[str, Any]:
        encoded_model = urllib.parse.quote(self.config.model_id, safe="")
        url = (
            f"https://bedrock-runtime.{self.config.region}.amazonaws.com"
            f"/model/{encoded_model}/converse"
        )
        payload = json.dumps(
            {"messages": messages, "inferenceConfig": {"maxTokens": max_tokens}}
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.bearer_token}",
            },
        )
        try:
            with self._urlopen(request, timeout=self.config.converse_timeout) as response:
                raw_body = response.read()
                status_code = getattr(response, "status", 200)
        except urllib.error.HTTPError as exc:
            body = self._decode_json(exc.read())
            self._raise_http_error(exc.code, body)
            raise AssertionError("unreachable")
        except (TimeoutError, socket.timeout) as exc:
            raise ProviderTimeoutError("Bedrock Converse request timed out") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise ProviderTimeoutError("Bedrock Converse request timed out") from exc
            raise ProviderError("Bedrock API request failed") from exc
        if status_code >= 400:
            self._raise_http_error(status_code, self._decode_json(raw_body))
        return self._decode_json(raw_body)

    def _converse_with_sdk(
        self, messages: list[dict[str, Any]], max_tokens: int
    ) -> Mapping[str, Any]:
        if self._runtime_client is None:
            raise ProviderError("Bedrock SDK client is not initialized")
        try:
            return self._run_with_timeout(
                self._runtime_client.converse,
                self.config.converse_timeout,
                modelId=self.config.model_id,
                messages=messages,
                inferenceConfig={"maxTokens": max_tokens},
            )
        except ProviderTimeoutError:
            raise
        except Exception as exc:
            self._raise_sdk_error(exc)
            raise AssertionError("unreachable")

    def list_text_models(self) -> list[dict[str, Any]]:
        if self.config.mock_mode:
            return []
        client = self._model_client
        if client is None:
            try:
                import boto3

                client = boto3.client("bedrock", region_name=self.config.region)
            except Exception as exc:
                raise ProviderError("Bedrock model client is not available") from exc
        try:
            response = self._run_with_timeout(
                client.list_foundation_models,
                self.config.list_models_timeout,
            )
        except ProviderTimeoutError:
            raise
        except Exception as exc:
            self._raise_sdk_error(exc)
            raise AssertionError("unreachable")
        models: list[dict[str, Any]] = []
        for item in response.get("modelSummaries", []):
            output_modalities = item.get("outputModalities") or []
            if "TEXT" not in output_modalities:
                continue
            models.append(
                {
                    "modelId": item.get("modelId", ""),
                    "modelName": item.get("modelName", ""),
                    "provider": item.get("providerName", ""),
                    "inputModalities": item.get("inputModalities", []),
                    "outputModalities": output_modalities,
                }
            )
        deduplicated: dict[str, dict[str, Any]] = {}
        for model in models:
            key = f"{model['provider']}::{model['modelName']}"
            current = deduplicated.get(key)
            if current is None or len(model["modelId"]) < len(current["modelId"]):
                deduplicated[key] = model
        return list(deduplicated.values())

    @staticmethod
    def _run_with_timeout(
        operation: Callable[..., Any], timeout: int, **kwargs: Any
    ) -> Any:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(operation, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise ProviderTimeoutError("Bedrock request timed out") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _normalize_messages(
        messages: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized = []
        for message in messages:
            role = str(message.get("role") or "user")
            content = message.get("content", "")
            if isinstance(content, str):
                content = [{"text": content}]
            elif not isinstance(content, Sequence):
                content = [{"text": str(content)}]
            normalized.append({"role": role, "content": list(content)})
        return normalized

    @staticmethod
    def _decode_json(raw_body: bytes) -> Mapping[str, Any]:
        try:
            result = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderResponseError("Bedrock returned an invalid JSON response") from exc
        if not isinstance(result, Mapping):
            raise ProviderResponseError("Bedrock returned an unexpected response")
        return result

    @staticmethod
    def _parse_converse_response(response: Mapping[str, Any]) -> str:
        try:
            parts = response["output"]["message"]["content"]
            text = "".join(str(part.get("text", "")) for part in parts)
        except (KeyError, TypeError) as exc:
            raise ProviderResponseError("Bedrock response does not contain text") from exc
        if not text:
            raise ProviderResponseError("Bedrock response contains empty text")
        return text

    def _raise_http_error(self, status_code: int, body: Mapping[str, Any]) -> None:
        message = str(body.get("message") or body.get("Message") or "")
        if status_code in (401, 403):
            raise ProviderAuthenticationError("Bedrock authentication failed")
        if status_code == 400 and "context" in message.lower():
            raise ProviderContextLimitError("Bedrock context limit exceeded")
        if status_code == 400:
            raise ProviderResponseError("Bedrock rejected the request")
        if status_code == 404:
            raise ProviderModelError("Bedrock model is unavailable")
        if status_code == 429:
            raise ProviderRateLimitError("Bedrock rate limit exceeded")
        raise ProviderError(f"Bedrock API failed with HTTP {status_code}")

    @staticmethod
    def _raise_sdk_error(exc: Exception) -> None:
        name = type(exc).__name__
        response = getattr(exc, "response", {})
        code = ""
        if isinstance(response, Mapping):
            error = response.get("Error", {})
            if isinstance(error, Mapping):
                code = str(error.get("Code") or "")
        marker = f"{name} {code}".lower()
        if "validation" in marker and "context" in str(exc).lower():
            raise ProviderContextLimitError("Bedrock context limit exceeded") from exc
        if "accessdenied" in marker or "unauthorized" in marker:
            raise ProviderAccessError("Bedrock model access was denied") from exc
        if "throttl" in marker or "toomanyrequests" in marker:
            raise ProviderRateLimitError("Bedrock rate limit exceeded") from exc
        if "timeout" in marker:
            raise ProviderTimeoutError("Bedrock request timed out") from exc
        if "validation" in marker:
            raise ProviderResponseError("Bedrock rejected the request") from exc
        if "resourcenotfound" in marker:
            raise ProviderModelError("Bedrock model is unavailable") from exc
        raise ProviderError("Bedrock SDK request failed") from exc
