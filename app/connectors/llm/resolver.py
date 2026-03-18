"""Runtime provider selection for draft generation."""

from __future__ import annotations

import os
from collections.abc import Mapping

from app.connectors.llm.base import DraftGenerationProvider
from app.connectors.llm.fake import FakeLLMProvider
from app.connectors.llm.openai_provider import (
    OpenAIDraftGenerationProvider,
    OpenAIResponsesClientFactory,
)


def resolve_draft_generation_provider(
    *,
    environment: Mapping[str, str] | None = None,
    client_factory: OpenAIResponsesClientFactory | None = None,
) -> DraftGenerationProvider:
    """Resolve the runtime draft generation provider from environment."""

    resolved_environment = os.environ if environment is None else environment
    if "OPENAI_API_KEY" not in resolved_environment:
        return FakeLLMProvider()

    return OpenAIDraftGenerationProvider.from_environment(
        environment=resolved_environment,
        client_factory=client_factory,
    )
