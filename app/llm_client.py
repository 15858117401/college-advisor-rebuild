"""DeepSeek chat model client shared by future graph nodes."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.config import DeepSeekSettings


def build_deepseek_llm(
    settings: DeepSeekSettings | None = None,
) -> ChatOpenAI:
    """Create a LangChain chat model for DeepSeek's compatible endpoint."""

    active_settings = settings or DeepSeekSettings.from_env()
    return ChatOpenAI(
        api_key=active_settings.api_key,
        base_url=active_settings.base_url,
        model=active_settings.model,
        max_retries=2,
        timeout=60,
    )
