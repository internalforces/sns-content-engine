"""Channel-aware social draft generation service."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from app.config import AccountConfig, PromptProfileConfig
from app.connectors.llm import DraftGenerationProvider, DraftGenerationRequest
from app.services.prompt_renderer import PromptRenderer, build_domain_sensitivity
from app.services.topic_matching import contains_phrase, normalize_match_text, strip_urls
from app.storage import ContentBrief, SourcePolicyMode

_WHITESPACE_RE = re.compile(r"\s+")
_LINE_BREAK_RE = re.compile(r"\n{3,}")
_STRUCTURED_CHANNELS = frozenset({"linkedin", "threads"})
_STRUCTURED_SECTION_LABELS = (
    "1. One-line summary",
    "2. Key points",
    "3. Keywords",
    "4. Background/Context",
    "5. Forward impact",
    "6. Insight",
    "7. One-line conclusion",
    "8. URL",
)
_STRUCTURED_SECTION_LIMITS = {
    "1. One-line summary": 180,
    "2. Key points": 540,
    "3. Keywords": 160,
    "4. Background/Context": 320,
    "5. Forward impact": 320,
    "6. Insight": 320,
    "7. One-line conclusion": 160,
}


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


@dataclass(frozen=True, slots=True)
class RequiredSourceAttribution:
    """Compact attribution that generated restricted-source drafts must retain."""

    label: str
    candidates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChannelStyleGuidance:
    """Audience and tone guidance for a target publishing channel."""

    audience: str
    voice: str
    editorial_goal: str
    reader_focus: str
    implication_focus: str
    system_constraints: tuple[str, ...]
    user_constraints: tuple[str, ...]


class XDraftGenerator:
    """Generate validated social draft variants from stored content briefs."""

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
        channel: str = "x",
    ) -> tuple[str, ...]:
        _validate_variant_count(variant_count)

        if channel not in account.channels:
            raise DraftGenerationError(
                f"account {account_key!r} does not define channel {channel!r}"
            )

        channel_config = account.channels[channel]
        draft_link_url = resolve_draft_link_url(content_brief)
        render_context = _build_render_context(
            content_brief=content_brief,
            account_key=account_key,
            account=account,
            channel=channel,
            max_chars=channel_config.render.max_chars,
            draft_link_url=draft_link_url,
        )
        required_attribution = _build_required_source_attribution(content_brief)
        rendered_prompt = self._prompt_renderer.render(
            prompt_profile,
            context=render_context,
        )
        request = DraftGenerationRequest(
            channel=channel,
            system_prompt=_build_system_prompt(
                rendered_prompt.system_prompt,
                channel=channel,
                max_chars=channel_config.render.max_chars,
                variant_count=variant_count,
            ),
            user_prompt=_build_user_prompt(
                rendered_prompt.user_prompt,
                channel=channel,
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
        try:
            return _validate_variants(
                variants,
                request=request,
                required_attribution=required_attribution,
            )
        except DraftGenerationError as error:
            if channel not in _STRUCTURED_CHANNELS:
                raise

            retry_request = _build_structured_retry_request(
                request,
                failure_message=str(error),
            )
            retry_variants = self._llm_provider.generate_variants(retry_request)
            return _validate_variants(
                retry_variants,
                request=retry_request,
                required_attribution=required_attribution,
            )


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
    source_attribution = _build_source_attribution_label(provenance)
    sensitivity = build_domain_sensitivity(
        title=content_brief.title,
        summary=content_brief.summary,
        tags=tuple(content_brief.tags),
        topic=account.topic,
    )
    style = _channel_style_guidance(channel)
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
        "source_hostname": _source_hostname(provenance),
        "source_attribution": source_attribution,
        "article_summary": _article_summary(content_brief),
        "policy_mode": provenance.policy_mode.value if provenance.policy_mode is not None else None,
        "require_attribution": _require_attribution(content_brief),
        "sensitivity_domain": sensitivity.domain,
        "sensitivity_is_high_risk": sensitivity.is_high_risk,
        "sensitivity_matched_terms": sensitivity.matched_terms,
        "sensitivity_guidance": sensitivity.prompt_guidance,
        "sensitivity_review_note": sensitivity.review_note,
        "channel_audience": style.audience,
        "channel_voice": style.voice,
        "channel_editorial_goal": style.editorial_goal,
        "channel_reader_focus": style.reader_focus,
        "channel_implication_focus": style.implication_focus,
    }


def _build_system_prompt(
    base_prompt: str,
    *,
    channel: str,
    max_chars: int,
    variant_count: int,
) -> str:
    if channel == "x" or channel not in _STRUCTURED_CHANNELS:
        channel_label = _channel_label(channel)
        return (
            f"{base_prompt}\n\n"
            "Channel constraints:\n"
            f"- Output plain-text {channel_label} drafts only.\n"
            f"- Return exactly {variant_count} distinct variants.\n"
            f"- Keep every variant at or under {max_chars} characters.\n"
            "- Include the required URL exactly once in each variant.\n"
            "- Do not give investment advice, price targets, or buy/sell recommendations.\n"
            "- Attribute the insight to the source context instead of claiming certainty."
        )

    channel_label = _channel_label(channel)
    style = _channel_style_guidance(channel)
    return (
        f"{base_prompt}\n\n"
        "Channel constraints:\n"
        f"- Output plain-text {channel_label} drafts only.\n"
        f"- Return exactly {variant_count} distinct variants.\n"
        f"- Keep every variant at or under {max_chars} characters.\n"
        "- Use this exact numbered structure with line breaks:\n"
        "  1. One-line summary\n"
        "  2. Key points\n"
        "  3. Keywords\n"
        "  4. Background/Context\n"
        "  5. Forward impact\n"
        "  6. Insight\n"
        "  7. One-line conclusion\n"
        "  8. URL\n"
        "- Put 3 to 5 short bullet-style items inside section 2.\n"
        "- Put the required URL only in section 8.\n"
        "- Do not give investment advice, price targets, or buy/sell recommendations.\n"
        "- Attribute the insight to the source context instead of claiming certainty.\n"
        "- Keep each section skimmable for manual operator review.\n"
        + "\n".join(style.system_constraints)
    )


def _build_user_prompt(
    base_prompt: str,
    *,
    channel: str,
    landing_url: str,
    max_chars: int,
    variant_count: int,
) -> str:
    if channel == "x" or channel not in _STRUCTURED_CHANNELS:
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

    style = _channel_style_guidance(channel)
    return (
        f"{base_prompt}\n\n"
        "Output requirements:\n"
        f"- Variant count: {variant_count}\n"
        f"- Max characters per variant: {max_chars}\n"
        f"- Required URL: {landing_url}\n"
        "- Keep the numbered section labels exactly as written in the system instructions.\n"
        "- Section 2 should contain 3 to 5 bullet-style lines.\n"
        "- Section 3 should list concise keywords separated by commas.\n"
        + "\n".join(style.user_constraints)
        + "\n"
        "- Mention the source context when it helps credibility.\n"
        "- Avoid language that sounds like financial advice."
    )


def _build_structured_retry_request(
    request: DraftGenerationRequest,
    *,
    failure_message: str,
) -> DraftGenerationRequest:
    revision_note = (
        "\n\nRevision requirements:\n"
        f"- Previous attempt failed validation: {failure_message}\n"
        "- Retry from scratch.\n"
        "- Keep sections 1, 4, 5, 6, and 7 to one short sentence each.\n"
        "- Keep section 2 to exactly 3 short bullet lines.\n"
        "- Keep section 3 to a short comma-separated keyword list.\n"
        "- Put the exact required URL only in section 8.\n"
        "- Do not use bold markers, extra headings, or trailing notes."
    )
    return DraftGenerationRequest(
        channel=request.channel,
        system_prompt=f"{request.system_prompt}{revision_note}",
        user_prompt=f"{request.user_prompt}{revision_note}",
        landing_url=request.landing_url,
        max_chars=request.max_chars,
        variant_count=request.variant_count,
        title=request.title,
        key_points=request.key_points,
    )


def _channel_style_guidance(channel: str) -> ChannelStyleGuidance:
    if channel == "linkedin":
        return ChannelStyleGuidance(
            audience=(
                "operators, functional leaders, founders, investors, and other B2B "
                "decision-makers"
            ),
            voice="measured, executive-summary, and insight-led",
            editorial_goal=(
                "help a professional reader understand what changed, why it matters, "
                "and which strategic or operating signal to watch"
            ),
            reader_focus=(
                "Frame the update for managers, operators, and market-facing "
                "professionals who want decision-useful context."
            ),
            implication_focus=(
                "business impact, strategic context, execution risk, market "
                "relevance, or policy significance"
            ),
            system_constraints=(
                "- Write for operators, founders, investors, and functional leaders rather than general entertainment audiences.",
                "- Favor measured B2B language, executive-summary phrasing, and decision-useful context.",
                "- Highlight strategic, operational, market, or policy implications only when supported by the source.",
                "- Avoid casual slang, creator-style hype, or viral bait.",
            ),
            user_constraints=(
                "- Make section 1 read like an executive summary line for a professional audience.",
                "- Make section 5 explain the practical business, operating, market, or policy implication.",
                "- Make section 6 feel like a decision-useful takeaway for a professional reader.",
                "- Keep section 7 crisp and boardroom-ready rather than playful.",
            ),
        )

    if channel == "threads":
        return ChannelStyleGuidance(
            audience="broad social readers scanning quickly for timely, worth-sharing updates",
            voice="clear, lively, social-first, and factual",
            editorial_goal=(
                "help a fast-scrolling reader grasp the update quickly and see why "
                "it is worth sharing right now"
            ),
            reader_focus=(
                "Frame the update for curious social readers who want a quick, "
                "readable summary."
            ),
            implication_focus=(
                "why the update is timely, surprising, conversation-worthy, or "
                "useful to pass along right now"
            ),
            system_constraints=(
                "- Write for fast-scrolling social readers rather than formal corporate audiences.",
                "- Favor punchier, conversational phrasing while staying factual and sourced.",
                "- Surface the most talk-worthy, timely angle without becoming clickbait.",
                "- Avoid dense corporate jargon or over-explaining routine context.",
            ),
            user_constraints=(
                "- Make section 1 feel like a crisp hook grounded in the verified update.",
                "- Keep section 2 skimmable, concrete, and easy to quote back.",
                "- Make section 5 explain why people may care about or share this now.",
                "- Make section 6 feel timely and conversation-worthy without overclaiming.",
            ),
        )

    return ChannelStyleGuidance(
        audience="general social readers",
        voice="clear, concise, and factual",
        editorial_goal="help readers understand the verified update quickly",
        reader_focus="Frame the update for a broad social audience.",
        implication_focus="the clearest verified reason this update matters",
        system_constraints=(),
        user_constraints=(),
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


def _build_required_source_attribution(
    content_brief: ContentBrief,
) -> RequiredSourceAttribution | None:
    if not _require_attribution(content_brief):
        return None

    provenance = build_draft_provenance_snapshot(content_brief)
    label = _build_source_attribution_label(provenance)
    candidates = _build_source_attribution_candidates(provenance)
    if label is None or not candidates:
        return None

    return RequiredSourceAttribution(label=label, candidates=candidates)


def _build_source_attribution_label(provenance: DraftProvenanceSnapshot) -> str | None:
    source_name = _clean_attribution_candidate(provenance.source_name)
    hostname = _source_hostname(provenance)

    if source_name and _looks_like_human_source_name(source_name) and len(source_name) <= 36:
        return source_name

    return hostname or source_name


def _build_source_attribution_candidates(
    provenance: DraftProvenanceSnapshot,
) -> tuple[str, ...]:
    candidates: list[str] = []
    for candidate in (
        provenance.source_name,
        _extract_hostname(provenance.article_url),
        _extract_hostname(provenance.source_url),
        _build_source_attribution_label(provenance),
    ):
        cleaned = _clean_attribution_candidate(candidate)
        if cleaned:
            candidates.append(cleaned)

    return tuple(dict.fromkeys(candidates))


def _clean_attribution_candidate(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = _normalize_body(value)
    return cleaned or None


def _looks_like_human_source_name(value: str) -> bool:
    return not ("_" in value and " " not in value)


def _source_hostname(provenance: DraftProvenanceSnapshot) -> str | None:
    return _extract_hostname(provenance.article_url) or _extract_hostname(provenance.source_url)


def _extract_hostname(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlsplit(url)
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname or None


def _validate_variants(
    variants: tuple[str, ...],
    *,
    request: DraftGenerationRequest,
    required_attribution: RequiredSourceAttribution | None = None,
) -> tuple[str, ...]:
    if len(variants) != request.variant_count:
        raise DraftGenerationError(
            f"provider returned {len(variants)} variants, expected {request.variant_count}"
        )

    normalized_variants: list[str] = []
    seen: set[str] = set()

    for index, variant in enumerate(variants):
        normalized = _normalize_variant_body(variant, channel=request.channel)
        if not normalized:
            raise DraftGenerationError(f"variant {index} is empty after normalization")
        if _channel_uses_compaction(request.channel):
            if request.landing_url not in normalized:
                raise DraftGenerationError(f"variant {index} is missing the landing URL")
            normalized = _coerce_x_variant_to_fit(
                normalized,
                landing_url=request.landing_url,
                max_chars=request.max_chars,
                required_attribution=required_attribution,
            )
        elif request.channel in _STRUCTURED_CHANNELS:
            normalized = _coerce_structured_variant_to_fit(
                normalized,
                landing_url=request.landing_url,
                max_chars=request.max_chars,
            )
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


def _normalize_variant_body(value: str, *, channel: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    if channel not in _STRUCTURED_CHANNELS:
        return _normalize_body(normalized)

    normalized_lines: list[str] = []
    blank_pending = False
    for raw_line in normalized.split("\n"):
        stripped = _normalize_body(raw_line)
        if not stripped:
            blank_pending = True
            continue
        if blank_pending and normalized_lines:
            normalized_lines.append("")
        normalized_lines.append(stripped)
        blank_pending = False

    return _LINE_BREAK_RE.sub("\n\n", "\n".join(normalized_lines)).strip()


def _coerce_x_variant_to_fit(
    value: str,
    *,
    landing_url: str,
    max_chars: int,
    required_attribution: RequiredSourceAttribution | None,
) -> str:
    normalized = _normalize_body(value)
    if required_attribution is not None:
        return _coerce_x_variant_with_required_attribution(
            normalized,
            landing_url=landing_url,
            max_chars=max_chars,
            required_attribution=required_attribution,
        )

    return _coerce_variant_to_fit(normalized, landing_url=landing_url, max_chars=max_chars)


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


def _coerce_x_variant_with_required_attribution(
    value: str,
    *,
    landing_url: str,
    max_chars: int,
    required_attribution: RequiredSourceAttribution,
) -> str:
    attribution_text = _format_source_attribution(required_attribution.label)
    value_without_url = value.replace(landing_url, " ")
    if _contains_source_attribution(value, required_attribution):
        supporting_text = _strip_attribution_cues(
            value_without_url,
            required_attribution=required_attribution,
        )
    else:
        supporting_text = value_without_url

    return _fit_text_with_attribution_and_url(
        text=supporting_text,
        attribution_text=attribution_text,
        landing_url=landing_url,
        max_chars=max_chars,
    )


def _contains_source_attribution(
    value: str,
    required_attribution: RequiredSourceAttribution,
) -> bool:
    normalized_text = normalize_match_text(strip_urls(value))
    return any(
        contains_phrase(candidate, normalized_text)
        for candidate in required_attribution.candidates
    )


def _format_source_attribution(label: str) -> str:
    return f"Source: {label}"


def _strip_attribution_cues(
    value: str,
    *,
    required_attribution: RequiredSourceAttribution,
) -> str:
    cleaned = value
    labels = (required_attribution.label, *required_attribution.candidates)

    for label in dict.fromkeys(labels):
        escaped_label = re.escape(label)
        for pattern in (
            rf"\b(?:according to|per|via|from)\s+Source:\s*{escaped_label}\b\.?",
            rf"\b(?:the update is|this update is|source is)\s+Source:\s*{escaped_label}\b\.?",
            rf"\bSource:\s*{escaped_label}\b\.?",
            rf"\b(?:according to|per|via|from|reported by)\s+{escaped_label}\b\.?",
        ):
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(
        r"(?:[\s,;:.-]+(?:according to|per|via|from|reported by|the update is|this update is|source is))+$",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    return _normalize_body(_normalize_body(cleaned).rstrip(" ,;:.-"))


def _fit_text_with_attribution_and_url(
    *,
    text: str,
    attribution_text: str,
    landing_url: str,
    max_chars: int,
) -> str:
    suffix = f"{attribution_text} {landing_url}"
    available = max_chars - len(suffix)
    if available < 0:
        return suffix

    normalized_text = _normalize_body(text)
    if not normalized_text:
        return suffix

    supporting_limit = max(available - 1, 0)
    if supporting_limit == 0:
        return suffix

    shortened_text = _shorten_text(normalized_text, limit=supporting_limit)
    if not shortened_text:
        return suffix

    return f"{shortened_text} {suffix}".strip()


def _coerce_structured_variant_to_fit(
    value: str,
    *,
    landing_url: str,
    max_chars: int,
) -> str:
    if len(value) <= max_chars and landing_url in value:
        return value

    sections = _parse_structured_sections(value)
    if sections is None:
        return value

    rendered = _render_structured_sections(
        sections,
        landing_url=landing_url,
    )
    if len(rendered) <= max_chars:
        return rendered

    return value


def _parse_structured_sections(value: str) -> dict[str, list[str]] | None:
    labels = set(_STRUCTURED_SECTION_LABELS)
    sections = {label: [] for label in _STRUCTURED_SECTION_LABELS}
    current_label: str | None = None

    for raw_line in value.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line in labels:
            current_label = line
            continue
        if current_label is None:
            continue
        sections[current_label].append(line)

    parsed_section_count = sum(bool(sections[label]) for label in _STRUCTURED_SECTION_LABELS[:-1])
    if parsed_section_count == 0:
        return None

    return sections


def _render_structured_sections(
    sections: Mapping[str, list[str]],
    *,
    landing_url: str,
) -> str:
    lines: list[str] = []

    for label in _STRUCTURED_SECTION_LABELS[:-1]:
        lines.append(label)
        if label == "2. Key points":
            lines.extend(_render_structured_key_points(sections.get(label, ())))
            continue

        raw_content = " ".join(sections.get(label, ()))
        content = _normalize_body(raw_content)
        if content:
            lines.append(
                _shorten_text(
                    content,
                    limit=_STRUCTURED_SECTION_LIMITS[label],
                )
            )

    lines.extend(("8. URL", landing_url))
    return "\n".join(lines).strip()


def _render_structured_key_points(lines: list[str] | tuple[str, ...]) -> list[str]:
    normalized_items = [
        _normalize_body(re.sub(r"^[-*•]\s*", "", line))
        for line in lines
        if _normalize_body(line)
    ]
    selected_items = normalized_items[:5]
    if not selected_items:
        return []

    per_item_limit = max(
        48,
        _STRUCTURED_SECTION_LIMITS["2. Key points"] // len(selected_items),
    )
    return [
        f"- {_shorten_text(item, limit=per_item_limit)}"
        for item in selected_items
        if item
    ]


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


def _channel_uses_compaction(channel: str) -> bool:
    return channel == "x"


def _channel_label(channel: str) -> str:
    if channel == "linkedin":
        return "LinkedIn"
    if channel == "threads":
        return "Threads"
    if channel == "x":
        return "X"
    return channel


def _validate_variant_count(variant_count: int) -> None:
    if variant_count not in (2, 3):
        raise ValueError("variant_count must be 2 or 3")
