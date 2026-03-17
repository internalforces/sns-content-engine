"""Deterministic fake LLM provider used by tests and local workflows."""

from __future__ import annotations

import re

from app.connectors.llm.base import DraftGenerationRequest

_OPENING_PHRASES = (
    "Practical takeaway:",
    "Worth a look:",
    "Quick insight:",
)
_CTA_PHRASES = (
    "Read more:",
    "See the full breakdown:",
    "Get the details:",
)
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

        variants: list[str] = []
        for index in range(request.variant_count):
            opening = _OPENING_PHRASES[index]
            call_to_action = _CTA_PHRASES[index]
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


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).casefold() for match in _WORD_RE.finditer(text))


def _fit_text_with_url(*, prefix: str, landing_url: str, max_chars: int) -> str:
    suffix = f" {landing_url}"
    available = max_chars - len(suffix)
    if available <= 0:
        raise ValueError("max_chars is too small to include the landing URL")

    trimmed_prefix = _shorten_text(prefix, limit=available)
    return f"{trimmed_prefix}{suffix}".strip()


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
