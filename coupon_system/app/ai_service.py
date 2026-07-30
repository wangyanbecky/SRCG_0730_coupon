"""
AI Service module for Coupon System.

Provides:
- Coupon recommendation with personalized ranking and reasons
- Risk assessment for fraud detection
- Model listing from AWS Bedrock

Uses AWS Bedrock Converse API. Dual-mode support:
- API Key mode: Bearer token via AWS_BEARER_TOKEN_BEDROCK env var
- SDK mode: AWS credentials via boto3
Falls back to rule engine (mock mode) when AI is unavailable or AI_MOCK_MODE is enabled.

Reference: bedrock.service.txt — BedrockService pattern adapted for Python.
"""
import json
import logging
import urllib.parse
from datetime import datetime, timedelta

import requests
from config import Config

logger = logging.getLogger(__name__)


class AIService:
    """AI service with Bedrock Converse API integration and rule-engine fallback.

    Two completely separate paths (mirrors the TS BedrockService):
    - API Key:  raw HTTP POST with Bearer token  (AWS_BEARER_TOKEN_BEDROCK)
    - SDK:      boto3 bedrock-runtime.converse()  (AWS credentials)
    """

    def __init__(self):
        self.mock_mode = Config.AI_MOCK_MODE
        self.api_key = Config.AWS_BEARER_TOKEN_BEDROCK
        self.region = Config.AWS_REGION
        self.model_id = Config.BEDROCK_MODEL_ID
        self._bedrock_client = None

        # API Key takes priority over SDK credentials
        if self.api_key:
            logger.info("Bedrock API Key detected — using Bearer token authentication.")
            self.mock_mode = False
        elif not self.mock_mode:
            self._init_bedrock_sdk()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    @property
    def status(self) -> dict:
        """Return AI service status for UI display.

        Returns:
            {mode: 'bedrock_api'|'bedrock_sdk'|'mock',
             label: str,
             connected: bool,
             model: str,
             region: str}
        """
        if self.api_key:
            return {
                'mode': 'bedrock_api',
                'label': 'Bedrock API',
                'connected': True,
                'model': self.model_id,
                'region': self.region,
            }
        if not self.mock_mode and self._bedrock_client is not None:
            return {
                'mode': 'bedrock_sdk',
                'label': 'Bedrock SDK',
                'connected': True,
                'model': self.model_id,
                'region': self.region,
            }
        return {
            'mode': 'mock',
            'label': '规则引擎降级',
            'connected': False,
            'model': self.model_id,
            'region': self.region,
        }

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_bedrock_sdk(self):
        """Initialize Amazon Bedrock boto3 runtime client (SDK path)."""
        try:
            import boto3
            self._bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.region,
            )
            logger.info("Bedrock SDK client initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock SDK client: {e}")
            logger.warning("Falling back to mock mode.")
            self.mock_mode = True

    # ==================================================================
    # Core: Converse API
    # ==================================================================

    def _call_bedrock(self, prompt: str, max_tokens: int = 1024) -> str:
        """Call Bedrock Converse API with a single user message.

        Returns the text content of the assistant response.
        """
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        result = self._converse(messages, max_tokens)
        return result.get("content", "")

    def _converse(
        self,
        messages: list,
        max_tokens: int = 1024,
    ) -> dict:
        """Send a conversation to the Bedrock Converse API.

        messages format (Converse API):
            [{"role": "user"|"assistant", "content": [{"text": "..."}]}]

        Returns:
            {"content": str, "tokenUsage": {"inputTokens": int|None,
                                             "outputTokens": int|None}}
        """
        if self.mock_mode:
            raise RuntimeError("Bedrock not available (mock mode)")

        if self.api_key:
            return self._converse_with_api_key(messages, max_tokens)
        return self._converse_with_sdk(messages, max_tokens)

    # ------------------------------------------------------------------
    # SDK credentials path
    # ------------------------------------------------------------------

    def _converse_with_sdk(self, messages: list, max_tokens: int) -> dict:
        """SDK path: uses boto3 bedrock-runtime.converse()."""
        import concurrent.futures

        # Normalise messages to Converse API shape
        converse_messages = self._normalise_messages(messages)

        if self._bedrock_client is None:
            raise RuntimeError("Bedrock SDK client is not initialised")

        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self._bedrock_client.converse,
                    modelId=self.model_id,
                    messages=converse_messages,
                    inferenceConfig={"maxTokens": max_tokens},
                )
                response = future.result(
                    timeout=Config.BEDROCK_CONVERSE_TIMEOUT
                )
        except concurrent.futures.TimeoutError:
            raise RuntimeError(
                "Bedrock Converse request timed out after "
                f"{Config.BEDROCK_CONVERSE_TIMEOUT} seconds"
            )
        except Exception as exc:
            error_name = type(exc).__name__
            logger.error(
                "[AIService.converseWithSdk] Error: %s %s",
                error_name, str(exc),
            )

            if "ValidationException" in error_name:
                raise RuntimeError(f"Context limit exceeded: {exc}")
            if "AccessDenied" in error_name:
                raise RuntimeError(f"模型访问被拒绝: {exc}")
            raise

        return self._parse_converse_response(response)

    # ------------------------------------------------------------------
    # API Key path (Bearer token)
    # ------------------------------------------------------------------

    def _converse_with_api_key(self, messages: list, max_tokens: int) -> dict:
        """API Key path: raw HTTP POST with Bearer token.

        Endpoint (Converse API):
            POST https://bedrock-runtime.{region}.amazonaws.com
                 /model/{modelId}/converse
        """
        encoded_model = urllib.parse.quote(self.model_id, safe='')
        url = (
            f"https://bedrock-runtime.{self.region}.amazonaws.com"
            f"/model/{encoded_model}/converse"
        )

        payload = {
            "messages": self._normalise_messages(messages),
            "inferenceConfig": {"maxTokens": max_tokens},
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=Config.BEDROCK_CONVERSE_TIMEOUT,
            )
        except requests.Timeout:
            raise RuntimeError(
                "Bedrock Converse request timed out after "
                f"{Config.BEDROCK_CONVERSE_TIMEOUT} seconds"
            )
        except requests.RequestException as exc:
            logger.error(
                "[AIService.converseWithApiKey] Request error: %s", str(exc)
            )
            raise RuntimeError(f"Bedrock API request failed: {exc}")

        # Parse JSON body
        try:
            body = response.json()
        except ValueError:
            raise RuntimeError(
                f"Bedrock API returned non-JSON response "
                f"(HTTP {response.status_code})"
            )

        if not response.ok:
            logger.error(
                "[AIService.converseWithApiKey] HTTP Error: %s %s",
                response.status_code, json.dumps(body),
            )
            self._raise_http_error(response.status_code, body)

        return self._parse_converse_response(body)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_messages(messages: list) -> list:
        """Ensure messages are in Converse API format.

        Accepts either:
          [{"role": "...", "content": [{"text": "..."}]}]   (already canonical)
          [{"role": "...", "content": "..."}]                (legacy string)
        """
        normalised = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                content = [{"text": content}]
            elif not isinstance(content, list):
                content = [{"text": str(content)}]
            normalised.append({"role": msg["role"], "content": content})
        return normalised

    @staticmethod
    def _parse_converse_response(response: dict) -> dict:
        """Extract text + token usage from a Converse API response."""
        output = response.get("output", {})
        output_msg = output.get("message", {})
        content_parts = output_msg.get("content", [])
        content = content_parts[0].get("text", "") if content_parts else ""

        usage = response.get("usage", {})
        return {
            "content": content,
            "tokenUsage": {
                "inputTokens": usage.get("inputTokens"),
                "outputTokens": usage.get("outputTokens"),
            },
        }

    def _raise_http_error(self, status_code: int, body: dict):
        """Map HTTP error responses to user-friendly messages."""
        error_message = (
            body.get("message")
            or body.get("Message")
            or "Unknown error"
        )

        if status_code in (401, 403):
            raise RuntimeError(
                "Invalid Bedrock API Key. "
                "Please check your key and try again."
            )
        if status_code == 400 and "context" in error_message.lower():
            raise RuntimeError(f"Context limit exceeded: {error_message}")
        if status_code == 400:
            raise RuntimeError(f"请求错误: {error_message}")
        if status_code == 404:
            raise RuntimeError(f"模型不存在或未开通: {self.model_id}")
        if status_code == 429:
            raise RuntimeError("请求频率过高，请稍后再试。")

        raise RuntimeError(
            f"Bedrock API 错误 ({status_code}): {error_message}"
        )

    # ==================================================================
    # Model Listing
    # ==================================================================

    def list_text_models(self) -> list:
        """Retrieve Bedrock foundation models that support TEXT output.

        Matches the TS BedrockService.listTextModels() behaviour:
        - Filters to models with "TEXT" in outputModalities
        - Deduplicates by provider::modelName (keeps shortest modelId)

        Returns list of dicts:
            [{"modelId","modelName","provider","inputModalities","outputModalities"}]
        """
        import concurrent.futures

        try:
            import boto3
            bedrock_client = boto3.client(
                'bedrock', region_name=self.region
            )
        except Exception as exc:
            logger.warning(
                "Failed to create bedrock client for model listing: %s", exc
            )
            return []

        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    bedrock_client.list_foundation_models
                )
                response = future.result(
                    timeout=Config.BEDROCK_LIST_MODELS_TIMEOUT
                )
        except concurrent.futures.TimeoutError:
            logger.error(
                "Bedrock ListFoundationModels request timed out"
            )
            return []
        except Exception as exc:
            logger.error("Bedrock ListFoundationModels failed: %s", exc)
            return []

        model_summaries = response.get("modelSummaries", [])

        # Filter: only models with TEXT output
        text_models = [
            m for m in model_summaries
            if "TEXT" in (m.get("outputModalities") or [])
        ]

        all_models = []
        for m in text_models:
            all_models.append({
                "modelId": m.get("modelId", ""),
                "modelName": m.get("modelName", ""),
                "provider": m.get("providerName", ""),
                "inputModalities": m.get("inputModalities", []),
                "outputModalities": m.get("outputModalities", []),
            })

        # Deduplicate by provider::modelName — keep shortest modelId
        seen = {}
        for model in all_models:
            key = f"{model['provider']}::{model['modelName']}"
            existing = seen.get(key)
            if (
                not existing
                or len(model["modelId"]) < len(existing["modelId"])
            ):
                seen[key] = model

        return list(seen.values())

    # ==================================================================
    # Recommendation
    # ==================================================================

    def recommend_coupons(self, user, campaigns: list) -> list:
        """Rank campaigns and generate recommendation reasons for a user.

        Returns a list of dicts: [{campaign, reason, score}, ...]
        """
        if not campaigns:
            return []

        try:
            if not self.mock_mode:
                return self._ai_recommend(user, campaigns)
        except Exception as exc:
            logger.warning(
                "AI recommendation failed, using rule engine: %s", exc
            )

        return self._rule_recommend(user, campaigns)

    def _ai_recommend(self, user, campaigns: list) -> list:
        """Use Bedrock Converse AI to generate personalised recommendations."""
        campaign_list = []
        for c in campaigns:
            days_left = (
                (c.end_date - datetime.now()).days if c.end_date else 0
            )
            campaign_list.append({
                'id': c.id,
                'name': c.name,
                'amount': c.amount,
                'stock': c.stock,
                'days_left': days_left,
                'description': c.description or '',
            })

        prompt = (
            "You are a coupon recommendation engine. Based on the user's "
            "profile, rank the available coupons and provide a personalised "
            "recommendation reason for each.\n\n"
            f"User profile:\n"
            f"- Age: {user.age or 'unknown'}\n"
            f"- Gender: {user.gender or 'unknown'}\n"
            f"- Hobbies: {user.hobbies or 'unknown'}\n"
            f"- Occupation: {user.occupation or 'unknown'}\n"
            f"- Points: {user.points}\n\n"
            f"Available coupons:\n"
            f"{json.dumps(campaign_list, ensure_ascii=False, indent=2)}\n\n"
            "For each coupon, provide a ranked recommendation with a brief, "
            "personalised reason in Chinese (15-30 characters). Also assign "
            "a relevance score (0.0 to 1.0).\n\n"
            "Return ONLY valid JSON in this exact format:\n"
            '{"recommendations":[{"campaign_id":1,"reason":"reason text",'
            '"score":0.95},...]}\n'
        )

        response_text = self._call_bedrock(prompt)

        # Parse AI response
        try:
            if '```json' in response_text:
                response_text = (
                    response_text.split('```json')[1].split('```')[0]
                )
            elif '```' in response_text:
                response_text = (
                    response_text.split('```')[1].split('```')[0]
                )
            result = json.loads(response_text.strip())
            recommendations = result.get('recommendations', [])
        except (json.JSONDecodeError, KeyError):
            logger.warning(
                "Failed to parse AI recommendation response"
            )
            return self._rule_recommend(user, campaigns)

        # Map campaign IDs back to campaign objects
        campaign_map = {c.id: c for c in campaigns}
        ranked = []
        for item in recommendations:
            cid = item.get('campaign_id')
            if cid in campaign_map:
                ranked.append({
                    'campaign': campaign_map[cid],
                    'reason': item.get('reason', '为您精选推荐'),
                    'score': item.get('score', 0.5),
                })

        return ranked

    def _rule_recommend(self, user, campaigns: list) -> list:
        """Rule-engine fallback for recommendations.

        - Sort by urgency (close to expiry first)
        - Sort by amount (higher first) as secondary
        - Assign generic but plausible reasons
        """
        now = datetime.now()
        scored = []

        for c in campaigns:
            score = 0.5
            reason = "热门优惠券"

            days_left = (
                (c.end_date - now).days if c.end_date else 30
            )

            # 1. Near-expiry coupons get urgency boost
            if days_left <= 1:
                score += 0.3
                reason = "即将过期，抓紧领取！"
            elif days_left <= 3:
                score += 0.2
                reason = "限时优惠，即将截止"
            elif days_left <= 7:
                score += 0.1
                reason = "近期热门，推荐领取"

            # 2. High-value coupons
            if c.amount >= 100:
                score += 0.15
                if '抓紧' not in reason:
                    reason = "大额优惠，超值之选"
            elif c.amount >= 50:
                score += 0.1
                if reason == "热门优惠券":
                    reason = "实惠好券，值得拥有"

            # 3. Low stock urgency
            if 0 < c.stock <= 5:
                score += 0.15
                reason = f"仅剩{c.stock}张，手慢无！"
            elif c.stock <= 20:
                score += 0.05

            # 4. Personalisation based on user hobbies
            if user.hobbies and c.description:
                hobbies = (user.hobbies or '').split(',')
                for hobby in hobbies:
                    if hobby.strip() in (c.description or ''):
                        score += 0.1
                        reason = (
                            f"适合{hobby.strip()}爱好者的专属优惠"
                        )
                        break

            score = min(score, 1.0)

            scored.append({
                'campaign': c,
                'reason': reason,
                'score': round(score, 2),
            })

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored

    # ==================================================================
    # Risk Assessment
    # ==================================================================

    def assess_risk(self, user, action: str) -> dict:
        """Assess risk for a user action.

        Returns: {risk_score: float, decision: str, reason: str}
        decision: 'allow', 'block', 'review'
        """
        try:
            if not self.mock_mode:
                return self._ai_assess_risk(user, action)
        except Exception as exc:
            logger.warning(
                "AI risk assessment failed, using rule engine: %s", exc
            )

        return self._rule_assess_risk(user, action)

    def _ai_assess_risk(self, user, action: str) -> dict:
        """Use Bedrock Converse AI for risk assessment."""
        from app.models import RiskLog

        recent_logs = (
            RiskLog.query
            .filter_by(user_id=user.id)
            .order_by(RiskLog.created_at.desc())
            .limit(10)
            .all()
        )

        user_data = {
            'username': user.username,
            'age': user.age,
            'points': user.points,
            'created_at': (
                user.created_at.strftime('%Y-%m-%d')
                if user.created_at else ''
            ),
        }
        history = [
            {
                'action': log.action,
                'score': log.risk_score,
                'decision': log.decision,
                'time': (
                    log.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    if log.created_at else ''
                ),
            }
            for log in recent_logs
        ]

        prompt = (
            "You are a fraud detection system for a coupon platform. "
            "Assess the risk of a user action.\n\n"
            f"User: {json.dumps(user_data, ensure_ascii=False)}\n"
            f"Action: {action}\n"
            f"Recent risk history: "
            f"{json.dumps(history, ensure_ascii=False)}\n\n"
            "Return ONLY valid JSON:\n"
            '{"risk_score":0.0-1.0,"decision":"allow|block|review",'
            '"reason":"brief explanation in Chinese"}\n'
        )

        response_text = self._call_bedrock(prompt)

        try:
            if '```json' in response_text:
                response_text = (
                    response_text.split('```json')[1].split('```')[0]
                )
            elif '```' in response_text:
                response_text = (
                    response_text.split('```')[1].split('```')[0]
                )
            result = json.loads(response_text.strip())
            return {
                'risk_score': float(result.get('risk_score', 0.0)),
                'decision': result.get('decision', 'allow'),
                'reason': result.get('reason', 'AI风险评估'),
            }
        except (json.JSONDecodeError, KeyError, ValueError):
            return self._rule_assess_risk(user, action)

    def _rule_assess_risk(self, user, action: str) -> dict:
        """Rule-engine risk assessment.

        - Count claims in the last RISK_CLAIM_WINDOW_SECONDS
        - > RISK_MAX_CLAIMS_IN_WINDOW → block
        - > RISK_MAX_CLAIMS_IN_WINDOW / 2 → review
        - Otherwise → allow
        """
        from app.models import RiskLog

        window_start = datetime.now() - timedelta(
            seconds=Config.RISK_CLAIM_WINDOW_SECONDS
        )

        recent_count = (
            RiskLog.query
            .filter(
                RiskLog.user_id == user.id,
                RiskLog.action == action,
                RiskLog.created_at >= window_start,
            )
            .count()
        )

        risk_score = min(
            recent_count / Config.RISK_MAX_CLAIMS_IN_WINDOW, 1.0
        )

        if recent_count > Config.RISK_MAX_CLAIMS_IN_WINDOW:
            decision = 'block'
            reason = (
                f'检测到异常高频操作：{Config.RISK_CLAIM_WINDOW_SECONDS}秒内'
                f'{recent_count}次{action}请求'
            )
        elif recent_count > Config.RISK_MAX_CLAIMS_IN_WINDOW // 2:
            decision = 'review'
            reason = (
                f'操作频率偏高：{Config.RISK_CLAIM_WINDOW_SECONDS}秒内'
                f'{recent_count}次{action}请求，需人工审核'
            )
        else:
            decision = 'allow'
            reason = '正常操作频率'

        return {
            'risk_score': round(risk_score, 2),
            'decision': decision,
            'reason': reason,
        }


# Singleton instance
ai_service = AIService()
