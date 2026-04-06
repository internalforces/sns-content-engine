"""Jinja-backed prompt rendering for draft generation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from jinja2 import Environment, StrictUndefined, TemplateError

from app.config import PromptProfileConfig
from app.services.topic_matching import contains_phrase, normalize_match_text


class PromptRenderingError(ValueError):
    """Raised when prompt templates cannot be rendered safely."""


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    """Rendered prompt pair for downstream generation."""

    system_prompt: str
    user_prompt: str


@dataclass(frozen=True, slots=True)
class DomainSensitivity:
    """Lightweight rule-based sensitivity signal for higher-risk topics."""

    domain: str | None = None
    matched_terms: tuple[str, ...] = ()
    prompt_guidance: str | None = None
    review_note: str | None = None

    @property
    def is_high_risk(self) -> bool:
        return self.domain is not None


@dataclass(frozen=True, slots=True)
class _DomainSensitivityRule:
    domain: str
    keywords: tuple[str, ...]
    prompt_guidance: str
    review_note: str


_DOMAIN_SENSITIVITY_RULES: tuple[_DomainSensitivityRule, ...] = (
    _DomainSensitivityRule(
        domain="politics",
        keywords=(
            "politics",
            "political",
            "election",
            "elections",
            "government",
            "congress",
            "senate",
            "parliament",
            "campaign",
            "president",
            "prime minister",
            "vote",
            "voting",
        ),
        prompt_guidance=(
            "Use non-partisan, attributed phrasing and avoid projecting motives, outcomes, or "
            "election implications beyond the source."
        ),
        review_note=(
            "Politics coverage should stay sourced, non-partisan, and careful around evolving claims."
        ),
    ),
    _DomainSensitivityRule(
        domain="finance",
        keywords=(
            "finance",
            "financial",
            "market",
            "markets",
            "stock",
            "stocks",
            "investing",
            "investor",
            "investors",
            "earnings",
            "economy",
            "inflation",
            "interest rates",
            "price target",
            "ipo",
            "crypto",
        ),
        prompt_guidance=(
            "Avoid investment advice, directional calls, and overstated certainty about prices, "
            "returns, or market impact."
        ),
        review_note=(
            "Finance coverage should stay factual, attributed, and free of buy or sell language."
        ),
    ),
    _DomainSensitivityRule(
        domain="health",
        keywords=(
            "health",
            "medical",
            "medicine",
            "disease",
            "outbreak",
            "vaccine",
            "vaccines",
            "hospital",
            "hospitals",
            "patient",
            "patients",
            "treatment",
            "treatments",
            "clinical trial",
            "public health",
            "fda",
        ),
        prompt_guidance=(
            "Avoid medical advice and do not overstate efficacy, safety, or causality beyond what "
            "the source explicitly supports."
        ),
        review_note=(
            "Health coverage should stay attributed and cautious about safety, efficacy, and medical advice."
        ),
    ),
    _DomainSensitivityRule(
        domain="crime_or_disaster",
        keywords=(
            "crime",
            "police",
            "arrest",
            "suspect",
            "shooting",
            "murder",
            "disaster",
            "disasters",
            "earthquake",
            "flood",
            "wildfire",
            "hurricane",
            "storm",
            "explosion",
            "evacuation",
        ),
        prompt_guidance=(
            "Avoid graphic detail, unverified blame, or precise casualty claims unless the source "
            "clearly supports them."
        ),
        review_note=(
            "Crime and disaster coverage should stay restrained, attributed, and careful with fast-moving facts."
        ),
    ),
)


class PromptRenderer:
    """Render configured prompt templates with strict variable validation."""

    def __init__(self) -> None:
        self._environment = Environment(
            autoescape=False,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )

    def render(
        self,
        profile: PromptProfileConfig,
        *,
        context: Mapping[str, object],
    ) -> RenderedPrompt:
        return RenderedPrompt(
            system_prompt=self._render_template(profile.system_template, context=context),
            user_prompt=self._render_template(profile.user_template, context=context),
        )

    def _render_template(self, template: str, *, context: Mapping[str, object]) -> str:
        try:
            rendered = self._environment.from_string(template).render(**context)
        except TemplateError as exc:
            raise PromptRenderingError(f"failed to render prompt template: {exc}") from exc

        normalized = rendered.strip()
        if not normalized:
            raise PromptRenderingError("prompt template rendered to empty text")
        return normalized


def build_domain_sensitivity(
    *,
    title: str,
    summary: str | None = None,
    tags: Sequence[str] = (),
    topic: str | None = None,
) -> DomainSensitivity:
    """Infer a lightweight high-risk domain signal from brief context."""

    normalized_text = normalize_match_text(
        " ".join(value for value in (title, summary or "", topic or "", *tags) if value)
    )
    if not normalized_text:
        return DomainSensitivity()

    for rule in _DOMAIN_SENSITIVITY_RULES:
        matched_terms = tuple(
            keyword for keyword in rule.keywords if contains_phrase(keyword, normalized_text)
        )
        if not matched_terms:
            continue

        return DomainSensitivity(
            domain=rule.domain,
            matched_terms=matched_terms[:3],
            prompt_guidance=rule.prompt_guidance,
            review_note=rule.review_note,
        )

    return DomainSensitivity()
