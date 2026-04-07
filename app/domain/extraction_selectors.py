"""Shared helpers for validating source-specific extraction selectors."""

from __future__ import annotations

import re

EXTRACTION_SELECTOR_RE = re.compile(
    r"^(?P<tag>[A-Za-z][A-Za-z0-9_-]*)?"
    r"(?:#(?P<id_value>[A-Za-z][A-Za-z0-9_-]*))?"
    r"(?:\.(?P<class_name>[A-Za-z][A-Za-z0-9_-]*))?$"
)


def normalize_extraction_selector(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("selector must not be empty")

    match = EXTRACTION_SELECTOR_RE.fullmatch(normalized)
    if match is None or not any(match.group(name) for name in ("tag", "id_value", "class_name")):
        raise ValueError(
            "selector must use the limited CSS form tag, .class, #id, tag.class, tag#id, or #id.class"
        )

    tag = match.group("tag")
    id_value = match.group("id_value")
    class_name = match.group("class_name")
    return (
        f"{tag.casefold() if tag else ''}"
        f"{f'#{id_value.casefold()}' if id_value else ''}"
        f"{f'.{class_name.casefold()}' if class_name else ''}"
    )
