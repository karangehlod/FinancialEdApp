"""
LLM Factory — creates LLM instances with easy model switching.

Supports:
  1. Azure OpenAI  (preferred when AZURE_OPENAI_API_KEY is set)
  2. Direct OpenAI  (fallback when only OPENAI_API_KEY is set)

The factory pattern allows the rest of the codebase to switch models by
changing a single environment variable — no code changes required.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings

logger = logging.getLogger(__name__)


def build_llm(
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> BaseChatModel:
    """
    Build and return a LangChain chat model.

    Priority:
      1. Azure OpenAI  (if AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT are set)
      2. Direct OpenAI  (if OPENAI_API_KEY is set)
      3. Raises RuntimeError if neither is configured.

    Args:
        model:       Override the default deployment / model name.
        temperature: Override the default temperature.
        max_tokens:  Override the default max tokens.

    Returns:
        A LangChain BaseChatModel instance ready for invoke/ainvoke.
    """
    _temperature = temperature if temperature is not None else settings.CHAT_TEMPERATURE
    _max_tokens = max_tokens if max_tokens is not None else settings.CHAT_MAX_TOKENS

    # ── Azure OpenAI ──────────────────────────────────────────────────────
    if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
        from langchain_openai import AzureChatOpenAI

        deployment = model or settings.AZURE_OPENAI_DEPLOYMENT or "gpt-4o"
        logger.info("Using Azure OpenAI — deployment=%s", deployment)
        return AzureChatOpenAI(
            azure_deployment=deployment,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=_temperature,
            max_tokens=_max_tokens,
        )

    # ── Direct OpenAI ─────────────────────────────────────────────────────
    if settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        model_name = model or settings.AZURE_OPENAI_MODEL or "gpt-4o"
        logger.info("Using OpenAI — model=%s", model_name)
        return ChatOpenAI(
            model=model_name,
            api_key=settings.OPENAI_API_KEY,
            temperature=_temperature,
            max_tokens=_max_tokens,
        )

    raise RuntimeError(
        "No LLM configured. Set AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT "
        "or OPENAI_API_KEY in your environment."
    )


@lru_cache(maxsize=4)
def get_default_llm() -> BaseChatModel:
    """Cached singleton LLM instance using default settings."""
    return build_llm()
