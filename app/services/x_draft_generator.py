"""X-specific draft generation service."""

from __future__ import annotations

import re
from collections.abc import Mapping

from app.config import AccountConfig, PromptProfileConfig
from app.connectors.llm import DraftGenerationProvider, DraftGenerationRequest
from app.services.prompt_renderer import PromptRenderer
from app.storage import ContentBrief

_WHITESPACE_RE = re.compile(r"\s+")


class DraftGenerationError(ValueError):
    """Raised when generated draft variants fail validation."""


class XDraftGenerator:
    """Generate validated X-ready draft variants from stored content briefs."""

    def __init__(
        self,
        llm_provider: DraftGenerationProvider,
        *,
        prompt_renderer: PromptRenderer | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._prompt_renderer = prompt_renderer or PromptRenderer()

    def generate(
        self,
        *,
        content_brief: ContentBrief,
        account_key: str,
        account: AccountConfig,
        prompt_profile: PromptProfileConfig,
        variant_count: int,
    ) -> tuple[str, ...]:
        _validate_variant_count(variant_count)

        if "x" not in account.channels:
            raise DraftGenerationError(f"account {account_key!r} does not define an x channel")

        channel_config = account.channels["x"]
        render_context = _build_render_context(
            content_brief=content_brief,
            account_key=account_key,
            account=account,
            channel="x",
            max_chars=channel_config.render.max_chars,
        )
        rendered_prompt = self._prompt_renderer.render(
            prompt_profile,
            context=render_context,
        )
        request = DraftGenerationRequest(
            channel="x",
            system_prompt=_build_system_prompt(
                rendered_prompt.system_prompt,
                max_chars=channel_config.render.max_chars,
                variant_count=variant_count,
            ),
            user_prompt=_build_user_prompt(
                rendered_prompt.user_prompt,
                landing_url=content_brief.landing_url,
                max_chars=channel_config.render.max_chars,
                variant_count=variant_count,
            ),
            landing_url=content_brief.landing_url,
            max_chars=channel_config.render.max_chars,
            variant_count=variant_count,
            title=content_brief.title,
            key_points=tuple(content_brief.key_points),
        )
        variants = self._llm_provider.generate_variants(request)
        return _validate_variants(variants, request=request)


def _build_render_context(
    *,
    content_brief: ContentBrief,
    account_key: str,
    account: AccountConfig,
    channel: str,
    max_chars: int,
) -> Mapping[str, object]:
    return {
        "account_key": account_key,
        "topic": account.topic,
        "channel": channel,
        "max_chars": max_chars,
        "title": content_brief.title,
        "summary": content_brief.summary,
        "key_points": tuple(content_brief.key_points),
        "tags": tuple(content_brief.tags),
        "angle": content_brief.angle,
        "landing_url": content_brief.landing_url,
        "language": content_brief.language,
        "source_url": _source_url(content_brief),
        "source_name": _source_name(content_brief),
        "article_summary": _article_summary(content_brief),
        "policy_mode": _policy_mode(content_brief),
        "require_attribution": _require_attribution(content_brief),
    }


def _build_system_prompt(base_prompt: str, *, max_chars: int, variant_count: int) -> str:
    return (
        f"{base_prompt}\n\n"
        "Channel constraints:\n"
        "- Output plain-text X drafts only.\n"
        f"- Return exactly {variant_count} distinct variants.\n"
        f"- Keep every variant at or under {max_chars} characters.\n"
        "- Include the landing URL exactly once in each variant.\n"
        "- Do not give investment advice, price targets, or buy/sell recommendations.\n"
        "- Attribute the insight to the source context instead of claiming certainty."
    )


def _build_user_prompt(
    base_prompt: str,
    *,
    landing_url: str,
    max_chars: int,
    variant_count: int,
) -> str:
    return (
        f"{base_prompt}\n\n"
        "Output requirements:\n"
        f"- Variant count: {variant_count}\n"
        f"- Max characters per variant: {max_chars}\n"
        f"- Landing URL: {landing_url}\n"
        "- Keep the tone concise and traffic-oriented.\n"
        "- Mention the source context when it helps credibility.\n"
        "- Avoid language that sounds like financial advice."
    )


def _source_url(content_brief: ContentBrief) -> str | None:
    source_item = content_brief.source_item
    if source_item is None:
        return None
    enrichment = source_item.article_enrichment
    if enrichment is not None and enrichment.article_url:
        return enrichment.article_url
    return source_item.source_url


def _source_name(content_brief: ContentBrief) -> str | None:
    source_item = content_brief.source_item
    if source_item is None:
        return None
    enrichment = source_item.article_enrichment
    if enrichment is not None and enrichment.source_name:
        return enrichment.source_name
    return source_item.source_key


def _article_summary(content_brief: ContentBrief) -> str | None:
    source_item = content_brief.source_item
    if source_item is None or source_item.article_enrichment is None:
        return content_brief.summary
    return source_item.article_enrichment.regenerated_summary or content_brief.summary


def _policy_mode(content_brief: ContentBrief) -> str | None:
    source_item = content_brief.source_item
    if source_item is None:
        return None
    return source_item.policy_mode.value


def _require_attribution(content_brief: ContentBrief) -> bool:
    source_item = content_brief.source_item
    if source_item is None:
        return False
    return source_item.require_attribution


def _validate_variants(
    variants: tuple[str, ...],
    *,
    request: DraftGenerationRequest,
) -> tuple[str, ...]:
    if len(variants) != request.variant_count:
        raise DraftGenerationError(
            f"provider returned {len(variants)} variants, expected {request.variant_count}"
        )

    normalized_variants: list[str] = []
    seen: set[str] = set()

    for index, variant in enumerate(variants):
        normalized = _normalize_body(variant)
        if not normalized:
            raise DraftGenerationError(f"variant {index} is empty after normalization")
        if request.landing_url not in normalized:
            raise DraftGenerationError(f"variant {index} is missing the landing URL")
        if len(normalized) > request.max_chars:
            raise DraftGenerationError(
                f"variant {index} exceeds max_chars ({len(normalized)} > {request.max_chars})"
            )
        if normalized in seen:
            raise DraftGenerationError(f"variant {index} duplicates an earlier variant")

        seen.add(normalized)
        normalized_variants.append(normalized)

    return tuple(normalized_variants)


def _normalize_body(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def _validate_variant_count(variant_count: int) -> None:
    if variant_count not in (2, 3):
        raise ValueError("variant_count must be 2 or 3")
