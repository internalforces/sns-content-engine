"""X-specific draft generation service."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from app.config import AccountConfig, PromptProfileConfig
from app.connectors.llm import DraftGenerationProvider, DraftGenerationRequest
from app.services.prompt_renderer import PromptRenderer, build_domain_sensitivity
from app.storage import ContentBrief, SourcePolicyMode

_WHITESPACE_RE = re.compile(r"\s+")


class DraftGenerationError(ValueError):
    """Raised when generated draft variants fail validation."""


@dataclass(frozen=True, slots=True)
class DraftProvenanceSnapshot:
    """Stored source and policy provenance for a generated draft."""

    source_name: str | None
    source_url: str | None
    article_url: str | None
    published_at: datetime | None
    policy_mode: SourcePolicyMode | None


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
        draft_link_url = resolve_draft_link_url(content_brief)
        render_context = _build_render_context(
            content_brief=content_brief,
            account_key=account_key,
            account=account,
            channel="x",
            max_chars=channel_config.render.max_chars,
            draft_link_url=draft_link_url,
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
                landing_url=draft_link_url,
                max_chars=channel_config.render.max_chars,
                variant_count=variant_count,
            ),
            landing_url=draft_link_url,
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
    draft_link_url: str,
) -> Mapping[str, object]:
    provenance = build_draft_provenance_snapshot(content_brief)
    sensitivity = build_domain_sensitivity(
        title=content_brief.title,
        summary=content_brief.summary,
        tags=tuple(content_brief.tags),
        topic=account.topic,
    )
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
        "landing_url": draft_link_url,
        "content_landing_url": content_brief.landing_url,
        "language": content_brief.language,
        "source_url": provenance.article_url or provenance.source_url,
        "article_url": provenance.article_url,
        "original_source_url": provenance.source_url,
        "source_name": provenance.source_name,
        "article_summary": _article_summary(content_brief),
        "policy_mode": provenance.policy_mode.value if provenance.policy_mode is not None else None,
        "require_attribution": _require_attribution(content_brief),
        "sensitivity_domain": sensitivity.domain,
        "sensitivity_is_high_risk": sensitivity.is_high_risk,
        "sensitivity_matched_terms": sensitivity.matched_terms,
        "sensitivity_guidance": sensitivity.prompt_guidance,
        "sensitivity_review_note": sensitivity.review_note,
    }


def _build_system_prompt(base_prompt: str, *, max_chars: int, variant_count: int) -> str:
    return (
        f"{base_prompt}\n\n"
        "Channel constraints:\n"
        "- Output plain-text X drafts only.\n"
        f"- Return exactly {variant_count} distinct variants.\n"
        f"- Keep every variant at or under {max_chars} characters.\n"
        "- Include the required URL exactly once in each variant.\n"
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
        f"- Required URL: {landing_url}\n"
        "- Keep the tone concise and traffic-oriented.\n"
        "- Mention the source context when it helps credibility.\n"
        "- Avoid language that sounds like financial advice."
    )


def resolve_draft_link_url(content_brief: ContentBrief) -> str:
    """Return the URL that generated drafts should include."""

    provenance = build_draft_provenance_snapshot(content_brief)
    return provenance.article_url or content_brief.landing_url


def build_draft_provenance_snapshot(content_brief: ContentBrief) -> DraftProvenanceSnapshot:
    source_item = content_brief.source_item
    if source_item is None:
        return DraftProvenanceSnapshot(
            source_name=None,
            source_url=None,
            article_url=None,
            published_at=None,
            policy_mode=None,
        )

    enrichment = source_item.article_enrichment
    return DraftProvenanceSnapshot(
        source_name=_source_name(source_item.source_key, enrichment.source_name if enrichment else None),
        source_url=source_item.source_url,
        article_url=enrichment.article_url if enrichment is not None else None,
        published_at=(enrichment.published_at if enrichment and enrichment.published_at else source_item.published_at),
        policy_mode=source_item.policy_mode,
    )


def _article_summary(content_brief: ContentBrief) -> str | None:
    source_item = content_brief.source_item
    if source_item is None or source_item.article_enrichment is None:
        return content_brief.summary
    return source_item.article_enrichment.regenerated_summary or content_brief.summary


def _source_name(source_key: str, enrichment_source_name: str | None) -> str:
    if enrichment_source_name:
        return enrichment_source_name
    return source_key


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
        normalized = _coerce_variant_to_fit(
            normalized,
            landing_url=request.landing_url,
            max_chars=request.max_chars,
        )
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


def _coerce_variant_to_fit(value: str, *, landing_url: str, max_chars: int) -> str:
    normalized = _normalize_body(value)
    if len(normalized) <= max_chars:
        return normalized

    shortened = _fit_text_with_url(
        text=normalized.replace(landing_url, " "),
        landing_url=landing_url,
        max_chars=max_chars,
    )
    return _normalize_body(shortened)


def _fit_text_with_url(*, text: str, landing_url: str, max_chars: int) -> str:
    available = max_chars - len(landing_url)
    if available < 0:
        return landing_url

    normalized_text = _normalize_body(text)
    if not normalized_text:
        return landing_url

    supporting_limit = max(available - 1, 0)
    if supporting_limit == 0:
        return landing_url

    shortened_text = _shorten_text(normalized_text, limit=supporting_limit)
    if not shortened_text:
        return landing_url

    return f"{shortened_text} {landing_url}".strip()


def _shorten_text(text: str, *, limit: int) -> str:
    if limit <= 0:
        return ""

    normalized = _normalize_body(text)
    if len(normalized) <= limit:
        return normalized

    words = normalized.split(" ")
    kept_words: list[str] = []

    for word in words:
        candidate = word if not kept_words else f"{' '.join(kept_words)} {word}"
        if len(candidate) > limit:
            break
        kept_words.append(word)

    if not kept_words:
        return normalized[:limit].rstrip()

    shortened = " ".join(kept_words)
    if len(shortened) == limit:
        return shortened

    if len(shortened) + 4 <= limit:
        return f"{shortened} ..."

    return shortened


def _validate_variant_count(variant_count: int) -> None:
    if variant_count not in (2, 3):
        raise ValueError("variant_count must be 2 or 3")
