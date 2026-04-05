"""AI-powered metadata generation service for enriched articles.

Uses an LLM to produce structured metadata from article content:
  - thumbnail_prompt: visual description suitable for AI image generation
  - tags:             topic tags (up to 8), normalized to lowercase
  - seo_description:  short SEO-optimized description (max 160 chars)
  - classification:   content type label

The service is intentionally side-effect-free — it only produces a
MetadataGenerationResult and never writes to the database directly.
Callers (e.g. enrich_articles workflow) are responsible for persisting
the result into ArticleEnrichment.metadata_json and related fields.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.connectors.llm.text_generation import (
    TextGenerationProvider,
    TextGenerationRequest,
    resolve_text_generation_provider,
)

_WHITESPACE_RE = re.compile(r"\s+")

_KNOWN_CLASSIFICATIONS = frozenset(
    {"news", "analysis", "opinion", "tutorial", "product", "other"}
)

_SYSTEM_PROMPT = """\
You are a content metadata specialist. Given an article's title, text excerpt, \
and existing tags, produce structured metadata that helps with SEO, content \
classification, and visual thumbnail creation.

IMPORTANT: Your entire response must be a single valid JSON object with no \
markdown fences, no commentary, and no text outside the JSON.

Required JSON schema:
{
  "type": "object",
  "required": ["thumbnail_prompt", "tags", "seo_description", "classification"],
  "properties": {
    "thumbnail_prompt": {
      "type": "string",
      "description": "A vivid, specific description for an AI image generator \
to create a relevant thumbnail (1-2 sentences, no brand logos)"
    },
    "tags": {
      "type": "array",
      "minItems": 1,
      "maxItems": 8,
      "items": {"type": "string"},
      "description": "Lowercase topic tags relevant to the article"
    },
    "seo_description": {
      "type": "string",
      "maxLength": 160,
      "description": "A concise, keyword-rich description of the article for search engines"
    },
    "classification": {
      "type": "string",
      "enum": ["news", "analysis", "opinion", "tutorial", "product", "other"],
      "description": "Primary content type of the article"
    }
  }
}"""


# --------------------------------------------------------------------------- #
# Public types
# --------------------------------------------------------------------------- #


class MetadataGenerationError(ValueError):
    """Raised when metadata generation fails validation or parsing."""


@dataclass(frozen=True, slots=True)
class MetadataGenerationInput:
    """Input payload for metadata generation."""

    title: str
    article_text: str
    summary: str | None = None
    existing_tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.article_text.strip():
            raise ValueError("article_text must not be empty")


@dataclass(frozen=True, slots=True)
class MetadataGenerationResult:
    """Structured output from AI metadata generation."""

    thumbnail_prompt: str
    tags: tuple[str, ...]
    seo_description: str
    classification: str

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for storage in metadata_json."""
        return {
            "ai_thumbnail_prompt": self.thumbnail_prompt,
            "ai_tags": list(self.tags),
            "ai_seo_description": self.seo_description,
            "ai_classification": self.classification,
        }


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class MetadataGenerator:
    """Generate structured article metadata using an LLM provider.

    Usage::

        generator = MetadataGenerator(resolve_text_generation_provider())
        result = generator.generate(MetadataGenerationInput(
            title="OpenAI releases GPT-5",
            article_text="...",
            summary="OpenAI announced today...",
            existing_tags=("ai", "openai"),
        ))
        print(result.thumbnail_prompt)
        print(result.classification)
    """

    def __init__(self, llm_provider: TextGenerationProvider) -> None:
        self._llm_provider = llm_provider

    @classmethod
    def from_environment(cls, environment=None) -> "MetadataGenerator":
        """Build a MetadataGenerator using environment-resolved provider."""
        return cls(resolve_text_generation_provider(environment=environment))

    def generate(self, input: MetadataGenerationInput) -> MetadataGenerationResult:
        """Generate structured metadata for the given article input.

        Args:
            input: Article content to generate metadata for.

        Returns:
            MetadataGenerationResult with thumbnail_prompt, tags,
            seo_description, and classification.

        Raises:
            MetadataGenerationError: If the LLM response cannot be parsed
                or fails validation.
        """
        user_prompt = _build_user_prompt(input)
        request = TextGenerationRequest(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        raw_text = self._llm_provider.generate(request)
        return _parse_result(raw_text)


# --------------------------------------------------------------------------- #
# Prompt construction
# --------------------------------------------------------------------------- #


def _build_user_prompt(input: MetadataGenerationInput) -> str:
    parts = [f"Title: {input.title.strip()}"]

    if input.summary:
        summary = _truncate(input.summary.strip(), limit=300)
        parts.append(f"Summary: {summary}")

    excerpt = _truncate(input.article_text.strip(), limit=1500)
    parts.append(f"Article excerpt:\n{excerpt}")

    if input.existing_tags:
        tags_str = ", ".join(input.existing_tags)
        parts.append(f"Existing tags (may expand or replace): {tags_str}")

    parts.append("\nGenerate metadata JSON:")
    return "\n\n".join(parts)


def _truncate(text: str, *, limit: int) -> str:
    """Return text truncated to at most *limit* characters on a word boundary."""
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    if len(normalized) <= limit:
        return normalized
    # Truncate at last space before limit, add ellipsis
    cut = normalized[:limit].rsplit(" ", 1)[0]
    return f"{cut}..."


# --------------------------------------------------------------------------- #
# Response parsing and validation
# --------------------------------------------------------------------------- #


def _parse_result(raw_text: str) -> MetadataGenerationResult:
    """Parse and validate the LLM's JSON response into a typed result."""
    text = raw_text.strip()

    # Strip accidental markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MetadataGenerationError(
            "Metadata generation did not return valid JSON"
        ) from exc

    if not isinstance(parsed, dict):
        raise MetadataGenerationError(
            "Metadata generation response must be a JSON object"
        )

    thumbnail_prompt = _require_string(parsed, "thumbnail_prompt")
    tags_raw = _require_list(parsed, "tags")
    seo_description = _require_string(parsed, "seo_description")
    classification = _require_string(parsed, "classification")

    # Validate and normalize tags
    tags = _normalize_tags(tags_raw)
    if not tags:
        raise MetadataGenerationError(
            "Metadata generation returned an empty tags list"
        )

    # Validate classification
    normalized_cls = classification.strip().casefold()
    if normalized_cls not in _KNOWN_CLASSIFICATIONS:
        # Coerce unknown classifications to 'other' rather than failing hard
        normalized_cls = "other"

    # Validate seo_description length
    seo = seo_description.strip()
    if len(seo) > 160:
        seo = seo[:157] + "..."

    return MetadataGenerationResult(
        thumbnail_prompt=thumbnail_prompt.strip(),
        tags=tags,
        seo_description=seo,
        classification=normalized_cls,
    )


def _require_string(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise MetadataGenerationError(
            f"Metadata generation response is missing or invalid field: '{key}'"
        )
    stripped = value.strip()
    if not stripped:
        raise MetadataGenerationError(
            f"Metadata generation field '{key}' must not be empty"
        )
    return stripped


def _require_list(data: dict, key: str) -> list:
    value = data.get(key)
    if not isinstance(value, list):
        raise MetadataGenerationError(
            f"Metadata generation response is missing or invalid field: '{key}'"
        )
    return value


def _normalize_tags(tags_raw: list) -> tuple[str, ...]:
    """Normalize tags to lowercase, stripped strings; drop non-strings."""
    normalized: list[str] = []
    seen: set[str] = set()
    for item in tags_raw:
        if not isinstance(item, str):
            continue
        tag = item.strip().casefold()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
        if len(normalized) == 8:
            break
    return tuple(normalized)
