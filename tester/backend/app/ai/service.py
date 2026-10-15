"""Centralized AI Service for GitFlow Project Hub.

Provides:
- AIService singleton
- Strict environment variable secret keys resolution (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY)
- Strict secret redaction (tokens, passwords, bearer keys, AWS keys)
- Token budget capping and request timeouts (10s)
- Revision-specific LRU in-memory cache
- Graceful deterministic fallback when AI is disabled or keys are absent
"""

import asyncio
from collections import OrderedDict
import hashlib
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from app.ai.provider import (
    AIProvider,
    AnthropicProvider,
    DisabledProvider,
    GeminiProvider,
    MockProvider,
    OpenAIProvider,
)

logger = logging.getLogger(__name__)

# Secret redaction regular expressions
_BEARER_PATTERN = re.compile(r'(?i)\b(bearer\s+)([a-zA-Z0-9_\-\.\~]{8,})\b')
_AUTH_HEADER_PATTERN = re.compile(r'(?i)(authorization:\s*["\']?)(?:bearer\s+)?([^\s"\'\n]{8,})(["\']?)')
_AWS_KEY_PATTERN = re.compile(r'\b(AKIA[0-9A-Z]{16})\b')
_AWS_SECRET_PATTERN = re.compile(r'(?i)(aws_secret_access_key|aws_secret_key|secret_key)\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?')
_GITHUB_TOKEN_PATTERN = re.compile(r'\b(gh[pousr]_[a-zA-Z0-9]{36,}|github_pat_[a-zA-Z0-9_]{82})\b')
_PRIVATE_KEY_PATTERN = re.compile(r'-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----')
_KV_SECRET_PATTERN = re.compile(
    r'(?i)\b(password|passwd|pwd|secret|api_key|apikey|api\s+key|secret_key|secret\s+key|access_token|private_key|auth_token)\b(\s*[:=]\s*["\']?)([^"\'\s,\n;]+)(["\']?)'
)
_DATABASE_URL_PATTERN = re.compile(r'([a-zA-Z0-9+]+://[^:]+:)([^@]+)(@)')
_SLACK_TOKEN_PATTERN = re.compile(r'\bxox[baprs]-[0-9a-zA-Z-]{10,}\b')
_STRIPE_KEY_PATTERN = re.compile(r'\bsk_(?:live|test)_[0-9a-zA-Z]{24,}\b')
_GENERIC_KEY_PATTERN = re.compile(r'\b(?:sample_api_secret_key_[a-zA-Z0-9_-]+)\b')


def redact_secrets(text: str) -> str:
    """Mask tokens, passwords, bearer keys, and AWS keys from input text."""
    if not text:
        return text

    sanitized = _PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", text)
    sanitized = _BEARER_PATTERN.sub(r"\1[REDACTED_TOKEN]", sanitized)
    sanitized = _AUTH_HEADER_PATTERN.sub(r"\1[REDACTED]\3", sanitized)
    sanitized = _AWS_KEY_PATTERN.sub("[REDACTED_AWS_KEY]", sanitized)
    sanitized = _AWS_SECRET_PATTERN.sub(r"\1: [REDACTED_AWS_SECRET]", sanitized)
    sanitized = _GITHUB_TOKEN_PATTERN.sub("[REDACTED_GITHUB_TOKEN]", sanitized)
    sanitized = _DATABASE_URL_PATTERN.sub(r"\1[REDACTED]\3", sanitized)
    sanitized = _SLACK_TOKEN_PATTERN.sub("[REDACTED_SLACK_TOKEN]", sanitized)
    sanitized = _STRIPE_KEY_PATTERN.sub("[REDACTED_STRIPE_KEY]", sanitized)
    sanitized = _KV_SECRET_PATTERN.sub(r"\1\2[REDACTED]\4", sanitized)
    sanitized = _GENERIC_KEY_PATTERN.sub("[REDACTED_API_KEY]", sanitized)

    return sanitized


class RevisionLRUCache:
    """Revision-specific LRU in-memory cache for AI completions."""

    def __init__(self, capacity: int = 256) -> None:
        self.capacity = capacity
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def _make_key(self, repo_name: str, revision: str, query: str) -> str:
        digest = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        return f"{repo_name.strip().lower()}:{revision.strip().lower()}:{digest}"

    def get(self, repo_name: str, revision: str, query: str) -> Optional[Dict[str, Any]]:
        key = self._make_key(repo_name, revision, query)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, repo_name: str, revision: str, query: str, value: Dict[str, Any]) -> None:
        key = self._make_key(repo_name, revision, query)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)

    def invalidate_revision(self, repo_name: str, revision: Optional[str] = None) -> int:
        prefix = f"{repo_name.strip().lower()}:"
        if revision:
            prefix += f"{revision.strip().lower()}:"
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


class AIService:
    """Centralized AI Service managing providers, secret scrubbing, caching, and fallback."""

    def __init__(self) -> None:
        self.cache = RevisionLRUCache(capacity=256)
        self._custom_provider: Optional[AIProvider] = None
        self.timeout_seconds: float = 10.0
        self.max_prompt_chars: int = 12000
        self.max_tokens: int = 1000

    def set_provider(self, provider: Optional[AIProvider]) -> None:
        """Explicitly override AI provider (useful for testing)."""
        self._custom_provider = provider

    def get_provider(self) -> AIProvider:
        """Resolve AI provider based on environment variables."""
        if self._custom_provider is not None:
            return self._custom_provider

        # Check explicit mock override
        if os.getenv("MOCK_AI", "").strip().lower() in ("1", "true", "yes"):
            return MockProvider()

        provider_name = os.getenv("AI_PROVIDER", "").strip().lower()
        if provider_name == "mock":
            return MockProvider()
        elif provider_name == "openai" and os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider(timeout=self.timeout_seconds)
        elif provider_name == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
            return AnthropicProvider(timeout=self.timeout_seconds)
        elif provider_name == "gemini" and os.getenv("GEMINI_API_KEY"):
            return GeminiProvider(timeout=self.timeout_seconds)
        elif provider_name == "disabled":
            return DisabledProvider("AI explicitly disabled via AI_PROVIDER=disabled")

        # Autodetect from keys
        if os.getenv("GEMINI_API_KEY"):
            return GeminiProvider(timeout=self.timeout_seconds)
        elif os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider(timeout=self.timeout_seconds)
        elif os.getenv("ANTHROPIC_API_KEY"):
            return AnthropicProvider(timeout=self.timeout_seconds)

        return DisabledProvider("No AI API keys configured (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY)")

    def get_provider_status(self) -> Dict[str, Any]:
        """Return truthful status and diagnostics for AI configuration without exposing secrets."""
        # 1. Custom provider override
        if self._custom_provider is not None:
            if isinstance(self._custom_provider, MockProvider):
                return {
                    "configured": True,
                    "active_provider": "mock",
                    "active_model": "mock-v1",
                    "key_present": False,
                    "redaction_active": True,
                    "cache_size": len(self.cache),
                    "execution_mode": "mock_provider",
                    "status_message": "Mock AI provider active for offline testing and deterministic evaluation.",
                }
            elif isinstance(self._custom_provider, DisabledProvider):
                return {
                    "configured": False,
                    "active_provider": "none",
                    "active_model": "none",
                    "key_present": False,
                    "redaction_active": True,
                    "cache_size": len(self.cache),
                    "execution_mode": "deterministic_fallback",
                    "status_message": self._custom_provider.reason,
                }
            elif isinstance(self._custom_provider, OpenAIProvider):
                key_present = bool(self._custom_provider.api_key)
                return {
                    "configured": key_present,
                    "active_provider": "openai" if key_present else "none",
                    "active_model": self._custom_provider.model if key_present else "none",
                    "key_present": key_present,
                    "redaction_active": True,
                    "cache_size": len(self.cache),
                    "execution_mode": "real_provider" if key_present else "deterministic_fallback",
                    "status_message": f"Custom OpenAI provider ({self._custom_provider.model}) active.",
                }
            elif isinstance(self._custom_provider, AnthropicProvider):
                key_present = bool(self._custom_provider.api_key)
                return {
                    "configured": key_present,
                    "active_provider": "anthropic" if key_present else "none",
                    "active_model": self._custom_provider.model if key_present else "none",
                    "key_present": key_present,
                    "redaction_active": True,
                    "cache_size": len(self.cache),
                    "execution_mode": "real_provider" if key_present else "deterministic_fallback",
                    "status_message": f"Custom Anthropic provider ({self._custom_provider.model}) active.",
                }
            elif isinstance(self._custom_provider, GeminiProvider):
                key_present = bool(self._custom_provider.api_key)
                return {
                    "configured": key_present,
                    "active_provider": "gemini" if key_present else "none",
                    "active_model": self._custom_provider.model if key_present else "none",
                    "key_present": key_present,
                    "redaction_active": True,
                    "cache_size": len(self.cache),
                    "execution_mode": "real_provider" if key_present else "deterministic_fallback",
                    "status_message": f"Custom Gemini provider ({self._custom_provider.model}) active.",
                }

        # 2. Check explicit mock override
        if os.getenv("MOCK_AI", "").strip().lower() in ("1", "true", "yes") or os.getenv("AI_PROVIDER", "").strip().lower() == "mock":
            return {
                "configured": True,
                "active_provider": "mock",
                "active_model": "mock-v1",
                "key_present": False,
                "redaction_active": True,
                "cache_size": len(self.cache),
                "execution_mode": "mock_provider",
                "status_message": "Mock AI provider active for offline testing and deterministic evaluation.",
            }

        # 3. Check explicit provider setting
        provider_name = os.getenv("AI_PROVIDER", "").strip().lower()
        if provider_name == "disabled":
            return {
                "configured": False,
                "active_provider": "none",
                "active_model": "none",
                "key_present": False,
                "redaction_active": True,
                "cache_size": len(self.cache),
                "execution_mode": "deterministic_fallback",
                "status_message": "AI explicitly disabled via AI_PROVIDER=disabled. System operates with deterministic rules.",
            }

        if provider_name == "openai":
            key_present = bool(os.getenv("OPENAI_API_KEY", "").strip())
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
            return {
                "configured": key_present,
                "active_provider": "openai" if key_present else "none",
                "active_model": model if key_present else "none",
                "key_present": key_present,
                "redaction_active": True,
                "cache_size": len(self.cache),
                "execution_mode": "real_provider" if key_present else "deterministic_fallback",
                "status_message": f"OpenAI ({model}) active." if key_present else "OPENAI_API_KEY missing. Operating in deterministic fallback mode.",
            }

        if provider_name == "anthropic":
            key_present = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022").strip()
            return {
                "configured": key_present,
                "active_provider": "anthropic" if key_present else "none",
                "active_model": model if key_present else "none",
                "key_present": key_present,
                "redaction_active": True,
                "cache_size": len(self.cache),
                "execution_mode": "real_provider" if key_present else "deterministic_fallback",
                "status_message": f"Anthropic Claude ({model}) active." if key_present else "ANTHROPIC_API_KEY missing. Operating in deterministic fallback mode.",
            }

        if provider_name == "gemini":
            key_present = bool(os.getenv("GEMINI_API_KEY", "").strip())
            model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
            return {
                "configured": key_present,
                "active_provider": "gemini" if key_present else "none",
                "active_model": model if key_present else "none",
                "key_present": key_present,
                "redaction_active": True,
                "cache_size": len(self.cache),
                "execution_mode": "real_provider" if key_present else "deterministic_fallback",
                "status_message": f"Google Gemini ({model}) active." if key_present else "GEMINI_API_KEY missing. Operating in deterministic fallback mode.",
            }

        # 4. Autodetect from keys
        if os.getenv("GEMINI_API_KEY", "").strip():
            model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
            return {
                "configured": True,
                "active_provider": "gemini",
                "active_model": model,
                "key_present": True,
                "redaction_active": True,
                "cache_size": len(self.cache),
                "execution_mode": "real_provider",
                "status_message": f"Google Gemini ({model}) autodetected and active.",
            }
        elif os.getenv("OPENAI_API_KEY", "").strip():
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
            return {
                "configured": True,
                "active_provider": "openai",
                "active_model": model,
                "key_present": True,
                "redaction_active": True,
                "cache_size": len(self.cache),
                "execution_mode": "real_provider",
                "status_message": f"OpenAI ({model}) autodetected and active.",
            }
        elif os.getenv("ANTHROPIC_API_KEY", "").strip():
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022").strip()
            return {
                "configured": True,
                "active_provider": "anthropic",
                "active_model": model,
                "key_present": True,
                "redaction_active": True,
                "cache_size": len(self.cache),
                "execution_mode": "real_provider",
                "status_message": f"Anthropic Claude ({model}) autodetected and active.",
            }

        return {
            "configured": False,
            "active_provider": "none",
            "active_model": "none",
            "key_present": False,
            "redaction_active": True,
            "cache_size": len(self.cache),
            "execution_mode": "deterministic_fallback",
            "status_message": "No AI API keys configured (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY). System operates in deterministic fallback mode.",
        }

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the currently active provider with a minimal probe."""
        status = self.get_provider_status()
        if status["execution_mode"] == "deterministic_fallback":
            return {
                "success": False,
                "latency_ms": 0.0,
                "provider": status["active_provider"],
                "model": status["active_model"],
                "message": "Cannot test connection: No AI API key is configured. Operating in deterministic fallback mode.",
            }

        provider = self.get_provider()
        if status["execution_mode"] == "mock_provider":
            start = time.perf_counter()
            res = await provider.generate_completion(prompt="Ping probe test", max_tokens=5)
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": True,
                "latency_ms": latency,
                "provider": "mock",
                "model": res.get("model", "mock-v1"),
                "message": "Mock AI provider connection verified successfully (deterministic test mode).",
            }

        start = time.perf_counter()
        try:
            res = await asyncio.wait_for(
                provider.generate_completion(
                    prompt="Respond with PONG only.",
                    system_prompt="Diagnostic probe",
                    max_tokens=5,
                ),
                timeout=self.timeout_seconds,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            if res.get("ai_available", False) and not res.get("error"):
                return {
                    "success": True,
                    "latency_ms": latency,
                    "provider": res.get("provider", status["active_provider"]),
                    "model": res.get("model", status["active_model"]),
                    "message": f"Successfully connected to {res.get('provider')} ({res.get('model')}) in {latency}ms.",
                }
            else:
                err_text = res.get("error") or "Unknown provider probe error"
                return {
                    "success": False,
                    "latency_ms": latency,
                    "provider": status["active_provider"],
                    "model": status["active_model"],
                    "message": f"Provider probe failed: {redact_secrets(str(err_text))}",
                }
        except asyncio.TimeoutError:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": False,
                "latency_ms": latency,
                "provider": status["active_provider"],
                "model": status["active_model"],
                "message": f"Connection timed out after {self.timeout_seconds}s.",
            }
        except Exception as exc:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": False,
                "latency_ms": latency,
                "provider": status["active_provider"],
                "model": status["active_model"],
                "message": f"Connection failed: {redact_secrets(str(exc))}",
            }

    def _cap_prompt(self, prompt: str) -> str:
        """Cap prompt length to budget limits."""
        if len(prompt) <= self.max_prompt_chars:
            return prompt
        half = (self.max_prompt_chars - 200) // 2
        return (
            prompt[:half]
            + "\n\n... [Content truncated to respect token budget limits] ...\n\n"
            + prompt[-half:]
        )

    def _generate_deterministic_explanation(
        self,
        question: str,
        repo_name: str,
        context: Dict[str, Any],
        memories: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate structured deterministic explanation without external AI calls."""
        q_tokens = [w for w in re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', question.lower())]

        languages = context.get("languages", {})
        frameworks = context.get("frameworks", [])
        routes = context.get("routes", [])
        models = context.get("models", [])
        tests = context.get("tests", [])

        # Match relevant routes
        matching_routes = [
            r for r in routes
            if any(t in str(r.get("path", "")).lower() or t in str(r.get("function_name", "")).lower() for t in q_tokens)
        ][:5]

        # Match relevant models
        matching_models = [
            m for m in models
            if any(t in str(m.get("name", "")).lower() for t in q_tokens)
        ][:5]

        # Match memories
        mem_items = memories or []
        matching_memories = [
            mem for mem in mem_items
            if any(t in str(mem.get("title", "")).lower() or t in str(mem.get("content", "")).lower() for t in q_tokens)
        ][:3]

        citations: List[str] = []
        for r in matching_routes:
            citations.append(f"route:{r.get('path')}")
        for m in matching_models:
            citations.append(f"model:{m.get('name')}")
        for mem in matching_memories:
            citations.append(f"memory:{mem.get('title')}")

        # Construct response
        lines = [
            f"### Repository Insights: {repo_name}",
            "",
            "**Deterministic Architecture Analysis** (AI key offline or not configured):",
            f"- **Languages**: {', '.join(languages.keys()) if languages else 'Not detected'}",
            f"- **Frameworks**: {', '.join(frameworks) if frameworks else 'Standard'}",
        ]

        if matching_routes:
            lines.append("\n**Relevant Endpoints / Handlers**:")
            for r in matching_routes:
                lines.append(f"- `{r.get('method', 'GET')} {r.get('path')}` -> `{r.get('function_name', '')}`")

        if matching_models:
            lines.append("\n**Relevant Data Models**:")
            for m in matching_models:
                lines.append(f"- Model `{m.get('name')}` (table: `{m.get('table_name', 'n/a')}`)")

        if matching_memories:
            lines.append("\n**Project Memory & Guidelines**:")
            for mem in matching_memories:
                lines.append(f"- **{mem.get('title')}**: {mem.get('content')}")

        if not matching_routes and not matching_models and not matching_memories:
            lines.append(
                f"\nNo specific matching code elements found for keywords `{' '.join(q_tokens[:4])}`. "
                f"Repository contains {len(routes)} registered route(s), {len(models)} model(s), and {len(tests)} test(s)."
            )

        answer = "\n".join(lines)

        return {
            "ai_available": False,
            "provider": "deterministic_fallback",
            "model": "deterministic-v1",
            "answer": answer,
            "citations": citations,
            "cached": False,
            "source": "deterministic_policy",
            "execution_mode": "deterministic_fallback",
        }

    async def ask(
        self,
        question: str,
        repo_name: str,
        context: Dict[str, Any],
        ai_enabled: bool = True,
        revision: str = "HEAD",
    ) -> Dict[str, Any]:
        """Query repository intelligence with secret redaction, caching, and fallback.

        Returns:
            dict with: ai_available, provider, answer, model, cached, execution_mode
        """
        # Step 1: Check if AI is disabled
        if not ai_enabled:
            fallback = self._generate_deterministic_explanation(question, repo_name, context)
            return {
                "ai_available": False,
                "provider": "disabled",
                "answer": "AI assistance is currently disabled in settings for this repository.",
                "model": "none",
                "cached": False,
                "execution_mode": "deterministic_fallback",
            }

        # Step 2: Strict secret redaction
        clean_question = redact_secrets(question)
        clean_context_str = redact_secrets(str(context))

        # Step 3: Check LRU cache
        cached_result = self.cache.get(repo_name, revision, clean_question)
        if cached_result is not None:
            c_prov = cached_result.get("provider", "cache")
            c_mode = "mock_provider" if c_prov == "mock" else ("real_provider" if c_prov in ("openai", "anthropic", "gemini") else "deterministic_fallback")
            return {
                "ai_available": cached_result.get("ai_available", True),
                "provider": c_prov,
                "answer": cached_result.get("answer", ""),
                "model": cached_result.get("model", "cached"),
                "cached": True,
                "execution_mode": cached_result.get("execution_mode", c_mode),
            }

        provider = self.get_provider()
        if isinstance(provider, DisabledProvider):
            fallback = self._generate_deterministic_explanation(question, repo_name, context)
            return {
                "ai_available": False,
                "provider": "deterministic_fallback",
                "answer": fallback["answer"],
                "model": "deterministic-v1",
                "cached": False,
                "execution_mode": "deterministic_fallback",
            }

        # Step 4: Construct prompt with budget cap
        system_prompt = (
            "You are an expert software architect providing concise, authoritative analysis "
            f"for repository '{repo_name}'. Always cite specific files, routes, or models."
        )
        prompt_content = f"Repository Context:\n{clean_context_str}\n\nQuestion:\n{clean_question}"
        capped_prompt = self._cap_prompt(prompt_content)

        # Step 5: Execute provider completion with timeout guard
        try:
            res = await asyncio.wait_for(
                provider.generate_completion(
                    prompt=capped_prompt,
                    system_prompt=system_prompt,
                    max_tokens=self.max_tokens,
                ),
                timeout=self.timeout_seconds,
            )

            if not res.get("ai_available", False) or not res.get("text"):
                fallback = self._generate_deterministic_explanation(question, repo_name, context)
                return {
                    "ai_available": False,
                    "provider": res.get("provider", "fallback"),
                    "answer": fallback["answer"],
                    "model": res.get("model", "unknown"),
                    "cached": False,
                    "execution_mode": "deterministic_fallback",
                }

            prov_name = res.get("provider", "unknown")
            mode = "mock_provider" if prov_name == "mock" else "real_provider"
            result = {
                "ai_available": True,
                "provider": prov_name,
                "answer": res.get("text", "").strip(),
                "model": res.get("model", "unknown"),
                "cached": False,
                "execution_mode": mode,
            }

            # Cache the successful result
            self.cache.set(repo_name, revision, clean_question, result)
            return result

        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("AI provider failed or timed out (%s), using deterministic fallback", exc)
            fallback = self._generate_deterministic_explanation(question, repo_name, context)
            return {
                "ai_available": False,
                "provider": "deterministic_fallback",
                "answer": fallback["answer"],
                "model": "deterministic-v1",
                "cached": False,
                "execution_mode": "deterministic_fallback",
            }

    async def answer_repository_question(
        self,
        question: str,
        repo_name: str,
        index_data: Dict[str, Any],
        memories: List[Dict[str, Any]],
        commit_sha: Optional[str] = None,
        ai_enabled: bool = True,
    ) -> Dict[str, Any]:
        """Extended helper matching project_hub router expectations.

        Returns:
            dict with: ai_available, answer, citations, source, provider, model, cached, execution_mode
        """
        revision = commit_sha or "HEAD"

        if not ai_enabled:
            fallback = self._generate_deterministic_explanation(question, repo_name, index_data, memories)
            return {
                "ai_available": False,
                "answer": "AI assistance is currently disabled in settings for this repository.",
                "citations": [],
                "source": "deterministic_policy",
                "provider": "disabled",
                "model": "none",
                "cached": False,
                "execution_mode": "deterministic_fallback",
            }

        provider = self.get_provider()
        if isinstance(provider, DisabledProvider):
            fallback = self._generate_deterministic_explanation(question, repo_name, index_data, memories)
            return fallback

        # Ask provider
        context = {
            "index_data": index_data,
            "memories": memories,
        }
        res = await self.ask(
            question=question,
            repo_name=repo_name,
            context=context,
            ai_enabled=ai_enabled,
            revision=revision,
        )

        citations = []
        for r in index_data.get("routes", []):
            if any(t in str(r.get("path", "")).lower() for t in question.lower().split() if len(t) > 3):
                citations.append(f"route:{r.get('path')}")
        for m in index_data.get("models", []):
            if any(t in str(m.get("name", "")).lower() for t in question.lower().split() if len(t) > 3):
                citations.append(f"model:{m.get('name')}")
        for mem in memories:
            citations.append(f"memory:{mem.get('title')}")

        return {
            "ai_available": res["ai_available"],
            "answer": res["answer"],
            "citations": citations[:10],
            "source": res.get("provider", "ai_service"),
            "provider": res.get("provider", "ai_service"),
            "model": res.get("model", "unknown"),
            "cached": res.get("cached", False),
            "execution_mode": res.get("execution_mode", "deterministic_fallback"),
        }


# Global singleton instance
ai_service = AIService()
