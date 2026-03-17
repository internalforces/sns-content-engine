"""Jinja-backed prompt rendering for draft generation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from jinja2 import Environment, StrictUndefined, TemplateError

from app.config import PromptProfileConfig


class PromptRenderingError(ValueError):
    """Raised when prompt templates cannot be rendered safely."""


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    """Rendered prompt pair for downstream generation."""

    system_prompt: str
    user_prompt: str


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

