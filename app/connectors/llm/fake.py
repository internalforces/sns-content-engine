"""Deterministic fake LLM provider used by tests and local workflows."""

from __future__ import annotations

import re

from app.connectors.llm.base import DraftGenerationRequest

_OPENING_PHRASES = (
    "Practical takeaway:",
    "Worth a look:",
    "Quick insight:",
)
_GUIDE_CTA_PHRASES = (
    "Try this workflow:",
    "See the framework:",
    "Open the guide:",
)
_TOOL_CTA_PHRASES = (
    "Try the tool:",
    "See it in action:",
    "Open the tool:",
)
_STRUCTURED_SUMMARY_SUFFIXES = (
    "is the clearest verified update to watch.",
    "stands out as the update most worth a quick operator scan.",
    "is the development to keep on the immediate review list.",
)
_LINKEDIN_IMPACT_LINES = (
    "Next impact to monitor: how this update changes execution priorities, partner expectations, or market positioning.",
    "Forward impact: watch for downstream shifts in planning, compliance, capital allocation, or customer messaging.",
    "What changes next: teams may need to revisit operating assumptions, stakeholder narratives, or roadmap timing.",
)
_THREADS_IMPACT_LINES = (
    "Why it may spread now: this update gives people a quick, concrete reason to react, share, or compare notes.",
    "What people may watch next: the follow-on angle is whether this turns into a bigger public conversation fast.",
    "Why it matters right now: the development is easy to grasp and timely enough to travel beyond niche followers.",
)
_LINKEDIN_INSIGHT_LINES = (
    "Insight: treat this as a decision-useful signal for operators and business readers, not a final conclusion.",
    "Insight: the most useful takeaway is the directional change this creates for teams, partners, and decision-makers.",
    "Insight: this matters most as an operating or market signal rather than a headline to skim and forget.",
)
_THREADS_INSIGHT_LINES = (
    "Insight: the share-worthy angle is the verified development itself, not extra speculation layered on top.",
    "Insight: this lands best as a fast social takeaway people can pass along without losing the factual core.",
    "Insight: the value here is a clear, timely update that gives readers something concrete to talk about now.",
)
_LINKEDIN_CONCLUSION_LINES = (
    "Bottom line: keep the source-linked update in view before changing plans, positioning, or stakeholder messaging.",
    "Bottom line: review the source-linked details before adjusting decisions, operations, or external communication.",
    "Bottom line: the source-linked facts are where the real strategic and operating implications show up.",
)
_THREADS_CONCLUSION_LINES = (
    "Bottom line: this is the part people will likely quote, repost, and discuss first.",
    "Bottom line: the source-linked update gives readers a clean, timely takeaway to share.",
    "Bottom line: if this keeps moving, the linked report is the quickest factual place to start.",
)
_STRUCTURED_CHANNELS = frozenset({"linkedin", "threads"})
_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_PROMPT_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "account",
        "and",
        "are",
        "channel",
        "concise",
        "constraints",
        "count",
        "details",
        "draft",
        "drafts",
        "editor",
        "english",
        "exactly",
        "for",
        "full",
        "get",
        "include",
        "keep",
        "landing",
        "look",
        "max",
        "more",
        "only",
        "output",
        "outputs",
        "per",
        "plain",
        "post",
        "posts",
        "ready",
        "requirements",
        "return",
        "see",
        "short",
        "system",
        "text",
        "the",
        "tone",
        "traffic",
        "under",
        "url",
        "use",
        "user",
        "variant",
        "variants",
        "with",
        "write",
        "x",
        "you",
    }
)


class FakeLLMProvider:
    """Generate deterministic draft variants without external API calls."""

    def generate_variants(self, request: DraftGenerationRequest) -> tuple[str, ...]:
        if request.variant_count not in (2, 3):
            raise ValueError("variant_count must be 2 or 3")

        if request.channel in _STRUCTURED_CHANNELS:
            return _generate_structured_variants(request)

        variants: list[str] = []
        cta_phrases = _select_cta_phrases(request)
        for index in range(request.variant_count):
            opening = _OPENING_PHRASES[index]
            call_to_action = cta_phrases[index]
            key_point = _select_key_point(request.key_points, index=index)
            prompt_focus = _build_prompt_focus(request)
            prefix = _build_prefix(
                opening=opening,
                prompt_focus=prompt_focus,
                title=request.title,
                key_point=key_point,
                call_to_action=call_to_action,
            )
            variants.append(
                _fit_text_with_url(
                    prefix=prefix,
                    landing_url=request.landing_url,
                    max_chars=request.max_chars,
                )
            )

        return tuple(variants)


def _select_key_point(key_points: tuple[str, ...], *, index: int) -> str | None:
    if not key_points:
        return None
    point_index = min(index + 1, len(key_points) - 1)
    return key_points[point_index]


def _build_prefix(
    *,
    opening: str,
    prompt_focus: str | None,
    title: str,
    key_point: str | None,
    call_to_action: str,
) -> str:
    parts = [opening, title.rstrip(".")]
    if prompt_focus:
        parts.append(f"Cue: {prompt_focus}.")
    if key_point and key_point.casefold() != title.casefold():
        parts.append(key_point.rstrip("."))
    parts.append(call_to_action)
    return " ".join(part.strip() for part in parts if part and part.strip())


def _build_prompt_focus(request: DraftGenerationRequest) -> str | None:
    blocked_words = {
        *_tokenize(request.title),
        *(
            word
            for point in request.key_points
            for word in _tokenize(point)
        ),
        *_tokenize(request.landing_url),
    }
    prompt_words: list[str] = []
    seen: set[str] = set()

    for text in (request.system_prompt, request.user_prompt):
        for word in _tokenize(text):
            if word in blocked_words or word in _PROMPT_STOPWORDS or len(word) < 3:
                continue
            if word in seen:
                continue
            seen.add(word)
            prompt_words.append(word)
            if len(prompt_words) == 3:
                return " ".join(prompt_words)

    if not prompt_words:
        return None
    return " ".join(prompt_words)


def _select_cta_phrases(request: DraftGenerationRequest) -> tuple[str, ...]:
    landing_text = request.landing_url.casefold()
    prompt_text = " ".join((request.system_prompt, request.user_prompt)).casefold()

    if "/guides" in landing_text or any(
        marker in prompt_text for marker in ("guide", "framework", "workflow")
    ):
        return _GUIDE_CTA_PHRASES

    return _TOOL_CTA_PHRASES


def _generate_structured_variants(request: DraftGenerationRequest) -> tuple[str, ...]:
    variants: list[str] = []
    prompt_focus = _build_prompt_focus(request)
    keywords = _build_keywords(request)
    summary_suffixes = _structured_summary_suffixes(request.channel)
    impact_lines = _structured_impact_lines(request.channel)
    insight_lines = _structured_insight_lines(request.channel)
    conclusion_lines = _structured_conclusion_lines(request.channel)

    for index in range(request.variant_count):
        key_point = _select_key_point(request.key_points, index=index) or request.title
        secondary_point = _select_key_point(request.key_points, index=min(index + 1, request.variant_count - 1))
        title = request.title.rstrip(".")
        summary = _shorten_text(
            f"{title} {prompt_focus or summary_suffixes[index]}",
            limit=220,
        )
        key_points = [
            _shorten_text(f"Verified update: {title}.", limit=180),
            _shorten_text(f"Core detail: {key_point.rstrip('.')}.", limit=180),
            _shorten_text(
                f"Operator watchpoint: {(secondary_point or prompt_focus or title).rstrip('.')}.",
                limit=180,
            ),
        ]
        background = _shorten_text(
            _structured_background_line(
                request.channel,
                prompt_focus=prompt_focus,
                title=title,
            ),
            limit=240,
        )
        forward_impact = _shorten_text(
            impact_lines[index],
            limit=240,
        )
        insight = _shorten_text(
            insight_lines[index],
            limit=220,
        )
        conclusion = _shorten_text(
            conclusion_lines[index],
            limit=180,
        )
        body = "\n".join(
            [
                "1. One-line summary",
                summary,
                "2. Key points",
                *(f"- {point}" for point in key_points),
                "3. Keywords",
                ", ".join(keywords),
                "4. Background/Context",
                background,
                "5. Forward impact",
                forward_impact,
                "6. Insight",
                insight,
                "7. One-line conclusion",
                conclusion,
                "8. URL",
                request.landing_url,
            ]
        )
        variants.append(_fit_structured_text(body=body, request=request))

    return tuple(variants)


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).casefold() for match in _WORD_RE.finditer(text))


def _fit_text_with_url(*, prefix: str, landing_url: str, max_chars: int) -> str:
    suffix = f" {landing_url}"
    available = max_chars - len(suffix)
    if available <= 0:
        raise ValueError("max_chars is too small to include the landing URL")

    trimmed_prefix = _shorten_text(prefix, limit=available)
    return f"{trimmed_prefix}{suffix}".strip()


def _fit_structured_text(*, body: str, request: DraftGenerationRequest) -> str:
    normalized = body.strip()
    if len(normalized) <= request.max_chars:
        return normalized

    lines = normalized.split("\n")
    for index, line in enumerate(lines):
        if line in {
            "1. One-line summary",
            "2. Key points",
            "3. Keywords",
            "4. Background/Context",
            "5. Forward impact",
            "6. Insight",
            "7. One-line conclusion",
            "8. URL",
            request.landing_url,
        }:
            continue
        lines[index] = _shorten_text(line, limit=max(len(line) - 40, 24))
        candidate = "\n".join(lines).strip()
        if len(candidate) <= request.max_chars:
            return candidate

    return "\n".join(lines).strip()[: request.max_chars].rstrip()


def _build_keywords(request: DraftGenerationRequest) -> tuple[str, ...]:
    words = []
    seen: set[str] = set()

    for token in (*_tokenize(request.title), *(word for point in request.key_points for word in _tokenize(point))):
        if len(token) < 4 or token in seen:
            continue
        seen.add(token)
        words.append(token)
        if len(words) == 5:
            break

    if not words:
        return ("news", "update", request.channel)

    return tuple(word.title() for word in words)


def _structured_summary_suffixes(channel: str) -> tuple[str, ...]:
    if channel == "linkedin":
        return (
            "is the clearest verified update for operators and market watchers.",
            "stands out as the development most worth a quick executive scan.",
            "is the signal professionals may want on the immediate review list.",
        )
    if channel == "threads":
        return (
            "is the clearest verified update people will likely talk about next.",
            "stands out as the development most worth a fast social read.",
            "is the update most likely to travel once readers see the source context.",
        )
    return _STRUCTURED_SUMMARY_SUFFIXES


def _structured_background_line(channel: str, *, prompt_focus: str | None, title: str) -> str:
    focus = prompt_focus or title.lower()
    if channel == "linkedin":
        return (
            f"Source context centers on {focus} and keeps the post anchored to the originating report "
            "so professional readers can interpret the update with business and operating context."
        )
    if channel == "threads":
        return (
            f"Source context centers on {focus} and keeps the post anchored to the originating report "
            "so the update stays easy to share without losing the factual core."
        )
    return (
        f"Source context centers on {focus} and keeps the post anchored to the originating report."
    )


def _structured_impact_lines(channel: str) -> tuple[str, ...]:
    if channel == "linkedin":
        return _LINKEDIN_IMPACT_LINES
    if channel == "threads":
        return _THREADS_IMPACT_LINES
    return _LINKEDIN_IMPACT_LINES


def _structured_insight_lines(channel: str) -> tuple[str, ...]:
    if channel == "linkedin":
        return _LINKEDIN_INSIGHT_LINES
    if channel == "threads":
        return _THREADS_INSIGHT_LINES
    return _LINKEDIN_INSIGHT_LINES


def _structured_conclusion_lines(channel: str) -> tuple[str, ...]:
    if channel == "linkedin":
        return _LINKEDIN_CONCLUSION_LINES
    if channel == "threads":
        return _THREADS_CONCLUSION_LINES
    return _LINKEDIN_CONCLUSION_LINES


def _shorten_text(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split()).strip()
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
