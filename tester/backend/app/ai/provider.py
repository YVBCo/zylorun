"""AI Provider module for GitFlow Project Hub.

Provides abstract AIProvider base class and implementations for:
- OpenAIProvider
- AnthropicProvider
- GeminiProvider
- MockProvider (deterministic testing)
- DisabledProvider (fallback when no API key configured)
"""

from abc import ABC, abstractmethod
import logging
import os
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for all AI model providers."""

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Generate a text completion.

        Args:
            prompt: User prompt content.
            system_prompt: Optional system instruction prompt.
            max_tokens: Maximum completion tokens to generate.

        Returns:
            Dict containing:
                - text: The generated string.
                - model: Model identifier used.
                - provider: Name of provider (e.g. 'openai', 'gemini').
                - usage: Dict with token counts (prompt_tokens, completion_tokens, total_tokens).
                - finish_reason: Status string (e.g. 'stop', 'length').
        """
        pass


class DisabledProvider(AIProvider):
    """Fallback provider used when no API key is configured or AI is disabled."""

    def __init__(self, reason: str = "No AI provider configured") -> None:
        self.reason = reason

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        return {
            "text": "",
            "model": "disabled",
            "provider": "disabled",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "finish_reason": "disabled",
            "error": self.reason,
            "ai_available": False,
        }


class MockProvider(AIProvider):
    """Deterministic mock provider for unit testing and offline development."""

    def __init__(
        self,
        canned_responses: Optional[Dict[str, str]] = None,
        default_response: Optional[str] = None,
    ) -> None:
        self.canned_responses: Dict[str, str] = canned_responses or {}
        self.default_response = default_response or (
            "Deterministic mock response: repository context evaluated successfully."
        )
        self.calls: list[Dict[str, Any]] = []

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        call_entry = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
        }
        self.calls.append(call_entry)

        text = self.default_response
        for key, candidate in self.canned_responses.items():
            if key.lower() in prompt.lower():
                text = candidate
                break

        prompt_tokens = max(1, len(prompt.split()))
        completion_tokens = max(1, len(text.split()))

        return {
            "text": text,
            "model": "mock-v1",
            "provider": "mock",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "finish_reason": "stop",
            "ai_available": True,
        }


class OpenAIProvider(AIProvider):
    """OpenAI API provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.timeout = timeout
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return await DisabledProvider("OPENAI_API_KEY is not configured").generate_completion(
                prompt, system_prompt, max_tokens
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                res.raise_for_status()
                data = res.json()

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            usage = data.get("usage", {})

            return {
                "text": content,
                "model": data.get("model", self.model),
                "provider": "openai",
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                "finish_reason": choice.get("finish_reason", "stop"),
                "ai_available": True,
            }
        except httpx.TimeoutException as exc:
            logger.warning("OpenAI API request timed out after %.1fs: %s", self.timeout, exc)
            return {
                "text": "",
                "model": self.model,
                "provider": "openai",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "finish_reason": "timeout",
                "error": f"Request timed out after {self.timeout}s",
                "ai_available": False,
            }
        except Exception as exc:
            logger.error("OpenAI API call failed: %s", exc)
            return {
                "text": "",
                "model": self.model,
                "provider": "openai",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "finish_reason": "error",
                "error": str(exc),
                "ai_available": False,
            }


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self.timeout = timeout
        self.base_url = "https://api.anthropic.com/v1"

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return await DisabledProvider("ANTHROPIC_API_KEY is not configured").generate_completion(
                prompt, system_prompt, max_tokens
            )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=headers,
                )
                res.raise_for_status()
                data = res.json()

            content_blocks = data.get("content", [])
            text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            usage = data.get("usage", {})

            return {
                "text": text,
                "model": data.get("model", self.model),
                "provider": "anthropic",
                "usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                },
                "finish_reason": data.get("stop_reason", "stop"),
                "ai_available": True,
            }
        except httpx.TimeoutException as exc:
            logger.warning("Anthropic API request timed out after %.1fs: %s", self.timeout, exc)
            return {
                "text": "",
                "model": self.model,
                "provider": "anthropic",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "finish_reason": "timeout",
                "error": f"Request timed out after {self.timeout}s",
                "ai_available": False,
            }
        except Exception as exc:
            logger.error("Anthropic API call failed: %s", exc)
            return {
                "text": "",
                "model": self.model,
                "provider": "anthropic",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "finish_reason": "error",
                "error": str(exc),
                "ai_available": False,
            }


class GeminiProvider(AIProvider):
    """Google Gemini API provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.timeout = timeout
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return await DisabledProvider("GEMINI_API_KEY is not configured").generate_completion(
                prompt, system_prompt, max_tokens
            )

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        contents = [{"parts": [{"text": prompt}]}]
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()

            candidates = data.get("candidates", [])
            text = ""
            finish_reason = "stop"
            if candidates:
                cand = candidates[0]
                finish_reason = cand.get("finishReason", "stop")
                parts = cand.get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)

            usage_meta = data.get("usageMetadata", {})
            return {
                "text": text,
                "model": self.model,
                "provider": "gemini",
                "usage": {
                    "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                    "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                    "total_tokens": usage_meta.get("totalTokenCount", 0),
                },
                "finish_reason": finish_reason,
                "ai_available": True,
            }
        except httpx.TimeoutException as exc:
            logger.warning("Gemini API request timed out after %.1fs: %s", self.timeout, exc)
            return {
                "text": "",
                "model": self.model,
                "provider": "gemini",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "finish_reason": "timeout",
                "error": f"Request timed out after {self.timeout}s",
                "ai_available": False,
            }
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            return {
                "text": "",
                "model": self.model,
                "provider": "gemini",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "finish_reason": "error",
                "error": str(exc),
                "ai_available": False,
            }
