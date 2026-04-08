"""Focused tests for the server-rendered operator console shell."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import create_app


def test_console_shell_root_redirects_to_canonical_landing() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/console",
        params={
            "config_dir": "/tmp/operator-config",
            "database_url": "sqlite:///tmp/operator.db",
        },
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert (
        response.headers["location"]
        == "http://testserver/console/?config_dir=%2Ftmp%2Foperator-config&database_url=sqlite%3A%2F%2F%2Ftmp%2Foperator.db"
    )


def test_console_shell_landing_page_renders_navigation_and_context() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/console/",
        params={
            "config_dir": "/tmp/operator-config",
            "database_url": "sqlite:///tmp/operator.db",
        },
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Operator Console" in response.text
    assert "Console Home" in response.text
    assert "Runs &amp; Failures" in response.text
    assert "Pending Review" in response.text
    assert "/tmp/operator-config" in response.text
    assert "sqlite:///tmp/operator.db" in response.text
    assert "Manual review required" in response.text
    assert "Dry-run publish is the browser default" in response.text


def test_console_shell_static_asset_is_served() -> None:
    client = TestClient(create_app())

    response = client.get("/console/static/console.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert "--console-bg" in response.text
    assert ".console-shell" in response.text
