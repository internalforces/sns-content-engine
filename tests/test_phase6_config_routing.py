"""Tests for Phase 6 — Config-driven AI provider control.

Covers:
- RouteConfig / AIProvidersConfig / AccountAIConfig schema validation
- load_providers_config() loader (missing file, valid file, invalid file)
- RouteRegistry.from_config() — config-based route building
- RouteRegistry.with_account_override() — per-account AI preferences
- AccountConfig.ai field default and validation
- Backward compatibility: existing from_environment() still works
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.config.schemas import (
    AIProvidersConfig,
    AccountAIConfig,
    RouteConfig,
)
from app.connectors.routing.models import Route, StepKey
from app.connectors.routing.registry import RouteRegistry


# --------------------------------------------------------------------------- #
# RouteConfig schema validation
# --------------------------------------------------------------------------- #


def test_route_config_minimal_fields() -> None:
    route = RouteConfig(step="draft_generate", provider="anthropic")
    assert route.step == "draft_generate"
    assert route.provider == "anthropic"
    assert route.model is None
    assert route.priority == 1
    assert route.enabled is True
    assert route.params == {}


def test_route_config_full_fields() -> None:
    route = RouteConfig(
        step="tts_synthesize",
        provider="elevenlabs",
        model="eleven_multilingual_v2",
        priority=2,
        enabled=False,
        params={"voice_id": "abc123"},
    )
    assert route.model == "eleven_multilingual_v2"
    assert route.priority == 2
    assert route.enabled is False
    assert route.params["voice_id"] == "abc123"


def test_route_config_rejects_empty_step() -> None:
    with pytest.raises(Exception):
        RouteConfig(step="  ", provider="openai")


def test_route_config_rejects_empty_provider() -> None:
    with pytest.raises(Exception):
        RouteConfig(step="draft_generate", provider="")


def test_route_config_rejects_empty_model() -> None:
    with pytest.raises(Exception):
        RouteConfig(step="draft_generate", provider="openai", model="  ")


def test_route_config_rejects_priority_below_one() -> None:
    with pytest.raises(Exception):
        RouteConfig(step="draft_generate", provider="openai", priority=0)


# --------------------------------------------------------------------------- #
# AIProvidersConfig schema validation
# --------------------------------------------------------------------------- #


def test_ai_providers_config_defaults_to_empty_routes() -> None:
    config = AIProvidersConfig()
    assert config.routes == ()


def test_ai_providers_config_accepts_multiple_routes() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(step="draft_generate", provider="anthropic", priority=1),
            RouteConfig(step="draft_generate", provider="openai", priority=2),
        ]
    )
    assert len(config.routes) == 2


# --------------------------------------------------------------------------- #
# AccountAIConfig schema validation
# --------------------------------------------------------------------------- #


def test_account_ai_config_all_none_by_default() -> None:
    ai = AccountAIConfig()
    assert ai.llm_provider is None
    assert ai.llm_model is None
    assert ai.tts_provider is None
    assert ai.tts_model is None


def test_account_ai_config_accepts_partial_spec() -> None:
    ai = AccountAIConfig(llm_provider="anthropic")
    assert ai.llm_provider == "anthropic"
    assert ai.llm_model is None


def test_account_ai_config_accepts_full_spec() -> None:
    ai = AccountAIConfig(
        llm_provider="anthropic",
        llm_model="claude-opus-4-6",
        tts_provider="elevenlabs",
        tts_model="eleven_turbo_v2",
    )
    assert ai.llm_model == "claude-opus-4-6"
    assert ai.tts_model == "eleven_turbo_v2"


def test_account_ai_config_rejects_empty_provider() -> None:
    with pytest.raises(Exception):
        AccountAIConfig(llm_provider="  ")


def test_account_ai_config_rejects_empty_model() -> None:
    with pytest.raises(Exception):
        AccountAIConfig(llm_model="")


# --------------------------------------------------------------------------- #
# load_providers_config — file loading
# --------------------------------------------------------------------------- #


def test_load_providers_config_returns_empty_when_file_absent(tmp_path: Path) -> None:
    from app.config.loaders import load_providers_config

    result = load_providers_config(tmp_path / "providers.yaml")
    assert isinstance(result, AIProvidersConfig)
    assert result.routes == ()


def test_load_providers_config_loads_valid_yaml(tmp_path: Path) -> None:
    from app.config.loaders import load_providers_config

    yaml_text = textwrap.dedent("""
        routes:
          - step: draft_generate
            provider: anthropic
            model: claude-haiku-4-5-20251001
            priority: 1
          - step: draft_generate
            provider: openai
            model: gpt-5.4-mini
            priority: 2
    """)
    path = tmp_path / "providers.yaml"
    path.write_text(yaml_text)

    config = load_providers_config(path)
    assert len(config.routes) == 2
    assert config.routes[0].provider == "anthropic"
    assert config.routes[1].provider == "openai"
    assert config.routes[1].model == "gpt-5.4-mini"


def test_load_providers_config_loads_file_with_params(tmp_path: Path) -> None:
    from app.config.loaders import load_providers_config

    yaml_text = textwrap.dedent("""
        routes:
          - step: tts_synthesize
            provider: elevenlabs
            priority: 1
            params:
              voice_id: abc123
              language: en
    """)
    path = tmp_path / "providers.yaml"
    path.write_text(yaml_text)

    config = load_providers_config(path)
    assert config.routes[0].params["voice_id"] == "abc123"


def test_load_providers_config_rejects_invalid_yaml(tmp_path: Path) -> None:
    from app.config import ConfigLoadError, ConfigValidationError

    from app.config.loaders import load_providers_config

    path = tmp_path / "providers.yaml"
    path.write_text("routes: not_a_list\n")

    with pytest.raises((ConfigLoadError, ConfigValidationError, Exception)):
        load_providers_config(path)


def test_load_providers_config_rejects_route_with_empty_provider(tmp_path: Path) -> None:
    from app.config import ConfigValidationError

    from app.config.loaders import load_providers_config

    yaml_text = textwrap.dedent("""
        routes:
          - step: draft_generate
            provider: ""
    """)
    path = tmp_path / "providers.yaml"
    path.write_text(yaml_text)

    with pytest.raises((ConfigValidationError, Exception)):
        load_providers_config(path)


# --------------------------------------------------------------------------- #
# RouteRegistry.from_config() — config-driven route building
# --------------------------------------------------------------------------- #


def test_from_config_builds_routes_when_credentials_present() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(step="draft_generate", provider="anthropic", model="claude-haiku-4-5-20251001", priority=1),
            RouteConfig(step="draft_generate", provider="openai", model="gpt-5.4-mini", priority=2),
        ]
    )
    env = {"ANTHROPIC_API_KEY": "ant-key", "OPENAI_API_KEY": "sk-key"}

    registry = RouteRegistry.from_config(config, environment=env)
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)

    assert len(routes) == 2
    assert routes[0].provider == "anthropic"  # priority 1
    assert routes[1].provider == "openai"      # priority 2


def test_from_config_skips_routes_without_credentials() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(step="draft_generate", provider="anthropic", priority=1),
            RouteConfig(step="draft_generate", provider="openai", priority=2),
        ]
    )
    env = {"ANTHROPIC_API_KEY": "ant-key"}  # no OpenAI key

    registry = RouteRegistry.from_config(config, environment=env)
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)

    assert len(routes) == 1
    assert routes[0].provider == "anthropic"


def test_from_config_skips_disabled_routes() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(step="draft_generate", provider="anthropic", priority=1, enabled=False),
            RouteConfig(step="draft_generate", provider="openai", priority=2),
        ]
    )
    env = {"ANTHROPIC_API_KEY": "ant-key", "OPENAI_API_KEY": "sk-key"}

    registry = RouteRegistry.from_config(config, environment=env)
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)

    assert len(routes) == 1
    assert routes[0].provider == "openai"


def test_from_config_falls_back_to_env_detection_when_no_routes_credentialed() -> None:
    """When all config routes lack credentials, falls back to env-var detection."""
    config = AIProvidersConfig(
        routes=[
            RouteConfig(step="draft_generate", provider="anthropic", priority=1),
        ]
    )
    env = {"OPENAI_API_KEY": "sk-key"}  # only OpenAI key, not Anthropic

    registry = RouteRegistry.from_config(config, environment=env)
    # Fallback: env detection finds OpenAI
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)
    assert len(routes) == 1
    assert routes[0].provider == "openai"


def test_from_config_falls_back_to_env_detection_when_config_is_empty() -> None:
    config = AIProvidersConfig()  # no routes
    env = {"OPENAI_API_KEY": "sk-key"}

    registry = RouteRegistry.from_config(config, environment=env)
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)
    assert routes[0].provider == "openai"


def test_from_config_preserves_model_from_config() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(
                step="draft_generate",
                provider="anthropic",
                model="claude-opus-4-6",  # non-default model
                priority=1,
            ),
        ]
    )
    env = {"ANTHROPIC_API_KEY": "ant-key"}

    registry = RouteRegistry.from_config(config, environment=env)
    route = registry.resolve_routes(StepKey.DRAFT_GENERATE)[0]
    assert route.model == "claude-opus-4-6"


def test_from_config_passes_params_to_route() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(
                step="tts_synthesize",
                provider="elevenlabs",
                priority=1,
                params={"voice_id": "xyz"},
            ),
        ]
    )
    env = {"ELEVENLABS_API_KEY": "el-key"}

    registry = RouteRegistry.from_config(config, environment=env)
    route = registry.resolve_routes(StepKey.TTS_SYNTHESIZE)[0]
    assert route.get_param("voice_id") == "xyz"


def test_from_config_builds_codex_wrapper_route_when_credentials_present() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(
                step="draft_generate",
                provider="codex_wrapper",
                model="wrapper-model",
                priority=1,
            ),
            RouteConfig(step="draft_generate", provider="fake", priority=2),
        ]
    )
    env = {
        "CODEX_WRAPPER_API_KEY": "cw-key",
        "CODEX_WRAPPER_BASE_URL": "https://wrapper.example/v1",
    }

    registry = RouteRegistry.from_config(config, environment=env)
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)

    assert [route.provider for route in routes] == ["codex_wrapper", "fake"]
    assert routes[0].model == "wrapper-model"


def test_from_config_skips_codex_wrapper_without_base_url() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(step="draft_generate", provider="codex_wrapper", priority=1),
            RouteConfig(step="draft_generate", provider="fake", priority=2),
        ]
    )
    env = {"CODEX_WRAPPER_API_KEY": "cw-key"}

    registry = RouteRegistry.from_config(config, environment=env)
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)

    assert [route.provider for route in routes] == ["fake"]


def test_from_config_allows_fake_provider_without_credentials() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(step="draft_generate", provider="fake", priority=1),
        ]
    )
    env: dict[str, str] = {}  # no credentials at all

    registry = RouteRegistry.from_config(config, environment=env)
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)
    assert routes[0].provider == "fake"


def test_from_config_routes_sorted_by_priority() -> None:
    config = AIProvidersConfig(
        routes=[
            RouteConfig(step="draft_generate", provider="openai", priority=3),
            RouteConfig(step="draft_generate", provider="anthropic", priority=1),
            RouteConfig(step="draft_generate", provider="fake", priority=2),
        ]
    )
    env = {"OPENAI_API_KEY": "sk-key", "ANTHROPIC_API_KEY": "ant-key"}

    registry = RouteRegistry.from_config(config, environment=env)
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)

    # anthropic (1) → fake (2) → openai (3)
    assert [r.provider for r in routes] == ["anthropic", "fake", "openai"]


def test_from_config_unknown_provider_is_allowed() -> None:
    """Providers not in the known list are allowed for forward compatibility."""
    config = AIProvidersConfig(
        routes=[
            RouteConfig(step="draft_generate", provider="future_llm_provider", priority=1),
        ]
    )
    env: dict[str, str] = {}

    registry = RouteRegistry.from_config(config, environment=env)
    # Unknown provider is treated as credentialed (falls back to env detection is NOT done
    # because future_llm_provider is treated as always-available)
    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)
    assert routes[0].provider == "future_llm_provider"


# --------------------------------------------------------------------------- #
# RouteRegistry.with_account_override() — per-account AI preferences
# --------------------------------------------------------------------------- #


def _make_registry_with_two_llm_providers() -> RouteRegistry:
    """Build a registry with anthropic (priority 1) and openai (priority 2) for draft_generate."""
    return RouteRegistry(
        [
            Route(step_key=StepKey.DRAFT_GENERATE, provider="anthropic", model="claude-haiku-4-5-20251001", priority=1),
            Route(step_key=StepKey.DRAFT_GENERATE, provider="openai", model="gpt-5.4-mini", priority=2),
            Route(step_key=StepKey.METADATA_GENERATE, provider="anthropic", model="claude-haiku-4-5-20251001", priority=1),
        ]
    )


def test_with_account_override_no_op_when_ai_config_is_empty() -> None:
    registry = _make_registry_with_two_llm_providers()
    ai_config = AccountAIConfig()

    new_registry = registry.with_account_override(ai_config)
    assert new_registry is registry  # same object, no change


def test_with_account_override_promotes_llm_provider_to_top() -> None:
    registry = _make_registry_with_two_llm_providers()
    ai_config = AccountAIConfig(llm_provider="openai")  # prefer openai over anthropic

    new_registry = registry.with_account_override(ai_config)
    routes = new_registry.resolve_routes(StepKey.DRAFT_GENERATE)

    # openai should now be first (priority 0 overrides priority 2)
    assert routes[0].provider == "openai"
    assert routes[0].priority == 0


def test_with_account_override_applies_model_override() -> None:
    registry = _make_registry_with_two_llm_providers()
    ai_config = AccountAIConfig(llm_provider="anthropic", llm_model="claude-opus-4-6")

    new_registry = registry.with_account_override(ai_config)
    top_route = new_registry.resolve_routes(StepKey.DRAFT_GENERATE)[0]

    assert top_route.provider == "anthropic"
    assert top_route.model == "claude-opus-4-6"


def test_with_account_override_applies_to_all_llm_step_keys() -> None:
    registry = _make_registry_with_two_llm_providers()
    ai_config = AccountAIConfig(llm_provider="openai")

    new_registry = registry.with_account_override(ai_config)

    # metadata_generate should also be affected
    # BUT openai has no route for metadata_generate, so it's a no-op for that step
    meta_routes = new_registry.resolve_routes(StepKey.METADATA_GENERATE)
    assert meta_routes[0].provider == "anthropic"  # unchanged (openai not in metadata)


def test_with_account_override_silently_skips_when_provider_not_in_registry() -> None:
    """When the preferred provider has no route, override is silently skipped."""
    registry = RouteRegistry(
        [Route(step_key=StepKey.DRAFT_GENERATE, provider="openai", priority=1)]
    )
    ai_config = AccountAIConfig(llm_provider="anthropic")  # anthropic not in registry

    new_registry = registry.with_account_override(ai_config)
    routes = new_registry.resolve_routes(StepKey.DRAFT_GENERATE)

    # openai still first (anthropic route was not found, override skipped)
    assert routes[0].provider == "openai"


def test_with_account_override_tts_provider() -> None:
    registry = RouteRegistry(
        [
            Route(step_key=StepKey.TTS_SYNTHESIZE, provider="elevenlabs", priority=1),
            Route(step_key=StepKey.TTS_SYNTHESIZE, provider="google", priority=2),
        ]
    )
    ai_config = AccountAIConfig(tts_provider="google")  # prefer google over elevenlabs

    new_registry = registry.with_account_override(ai_config)
    routes = new_registry.resolve_routes(StepKey.TTS_SYNTHESIZE)

    assert routes[0].provider == "google"
    assert routes[0].priority == 0


def test_with_account_override_does_not_mutate_original_registry() -> None:
    registry = _make_registry_with_two_llm_providers()
    original_routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)

    ai_config = AccountAIConfig(llm_provider="openai", llm_model="gpt-5")
    registry.with_account_override(ai_config)

    # Original registry unchanged
    assert registry.resolve_routes(StepKey.DRAFT_GENERATE) == original_routes


# --------------------------------------------------------------------------- #
# AccountConfig.ai field integration
# --------------------------------------------------------------------------- #


def test_account_config_has_default_empty_ai_config(tmp_path: Path) -> None:
    """accounts.yaml without ai: block should default to empty AccountAIConfig."""
    import textwrap
    import yaml
    from app.config.schemas import AccountsFileConfig

    yaml_text = textwrap.dedent("""
        accounts:
          test_account:
            topic: "Test"
            source_sets:
              - main
            prompt_profile: default
            landing:
              fallback_url: https://example.com
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
    """)
    data = yaml.safe_load(yaml_text)
    config = AccountsFileConfig.model_validate(data)
    account = config.accounts["test_account"]

    assert isinstance(account.ai, AccountAIConfig)
    assert account.ai.llm_provider is None
    assert account.ai.tts_provider is None


def test_account_config_accepts_ai_block(tmp_path: Path) -> None:
    """accounts.yaml with ai: block should populate AccountAIConfig."""
    import textwrap
    import yaml
    from app.config.schemas import AccountsFileConfig

    yaml_text = textwrap.dedent("""
        accounts:
          premium_account:
            topic: "Premium"
            source_sets:
              - main
            prompt_profile: premium
            landing:
              fallback_url: https://example.com
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
            ai:
              llm_provider: anthropic
              llm_model: claude-opus-4-6
    """)
    data = yaml.safe_load(yaml_text)
    config = AccountsFileConfig.model_validate(data)
    account = config.accounts["premium_account"]

    assert account.ai.llm_provider == "anthropic"
    assert account.ai.llm_model == "claude-opus-4-6"
    assert account.ai.tts_provider is None


# --------------------------------------------------------------------------- #
# Backward compatibility
# --------------------------------------------------------------------------- #


def test_from_environment_still_works_after_phase6_changes() -> None:
    """The original from_environment() factory must continue to work."""
    env = {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "ant-test"}
    registry = RouteRegistry.from_environment(environment=env)

    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)
    providers = [r.provider for r in routes]
    assert "openai" in providers
    assert "anthropic" in providers


# --------------------------------------------------------------------------- #
# Bug-fix: from_environment registers all LLM step keys (debug.md fix)
# --------------------------------------------------------------------------- #


def test_from_environment_registers_metadata_and_image_prompt_steps_with_openai() -> None:
    """OPENAI_API_KEY must produce routes for all three LLM step keys."""
    env = {"OPENAI_API_KEY": "sk-test"}
    registry = RouteRegistry.from_environment(env)

    for step in (StepKey.DRAFT_GENERATE, StepKey.METADATA_GENERATE, StepKey.IMAGE_PROMPT_GENERATE):
        routes = registry.resolve_routes(step)
        assert len(routes) == 1, f"expected 1 route for {step!r}, got {len(routes)}"
        assert routes[0].provider == "openai"


def test_from_environment_registers_metadata_and_image_prompt_steps_with_anthropic() -> None:
    """ANTHROPIC_API_KEY must produce routes for all three LLM step keys."""
    env = {"ANTHROPIC_API_KEY": "sk-ant"}
    registry = RouteRegistry.from_environment(env)

    for step in (StepKey.DRAFT_GENERATE, StepKey.METADATA_GENERATE, StepKey.IMAGE_PROMPT_GENERATE):
        routes = registry.resolve_routes(step)
        assert len(routes) == 1, f"expected 1 route for {step!r}, got {len(routes)}"
        assert routes[0].provider == "anthropic"


def test_from_environment_registers_codex_wrapper_for_draft_generate_only() -> None:
    env = {
        "CODEX_WRAPPER_API_KEY": "cw-key",
        "CODEX_WRAPPER_BASE_URL": "https://wrapper.example/v1",
    }
    registry = RouteRegistry.from_environment(env)

    draft_routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)
    assert len(draft_routes) == 1
    assert draft_routes[0].provider == "codex_wrapper"

    for step in (StepKey.METADATA_GENERATE, StepKey.IMAGE_PROMPT_GENERATE):
        assert registry.resolve_routes(step) == []


def test_from_environment_preserves_existing_llm_order_when_codex_wrapper_is_available() -> None:
    env = {
        "OPENAI_API_KEY": "sk-test",
        "ANTHROPIC_API_KEY": "ant-test",
        "CODEX_WRAPPER_API_KEY": "cw-key",
        "CODEX_WRAPPER_BASE_URL": "https://wrapper.example/v1",
    }
    registry = RouteRegistry.from_environment(env)

    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)

    assert [route.provider for route in routes] == [
        "openai",
        "anthropic",
        "codex_wrapper",
    ]


def test_with_account_override_applies_to_metadata_and_image_prompt_via_env_registry() -> None:
    """with_account_override must work for metadata_generate and image_prompt_generate
    when the registry was built from env vars (regression for the debug.md bug)."""
    from app.config.schemas import AccountAIConfig as _AAC

    env = {"OPENAI_API_KEY": "sk-x", "ANTHROPIC_API_KEY": "sk-y"}
    registry = RouteRegistry.from_environment(env)
    overridden = registry.with_account_override(_AAC(llm_provider="anthropic", llm_model="claude-opus-4-6"))

    for step in (StepKey.DRAFT_GENERATE, StepKey.METADATA_GENERATE, StepKey.IMAGE_PROMPT_GENERATE):
        routes = overridden.resolve_routes(step)
        # Anthropic must be first (priority=0) with the overridden model
        assert routes[0].provider == "anthropic", f"{step!r}: expected anthropic at top"
        assert routes[0].priority == 0, f"{step!r}: expected priority 0"
        assert routes[0].model == "claude-opus-4-6", f"{step!r}: expected overridden model"


def test_from_environment_empty_env_yields_no_llm_routes() -> None:
    """No LLM credentials → all LLM steps return empty route lists."""
    registry = RouteRegistry.from_environment({})
    for step in (StepKey.DRAFT_GENERATE, StepKey.METADATA_GENERATE, StepKey.IMAGE_PROMPT_GENERATE):
        assert registry.resolve_routes(step) == [], f"{step!r} should have no routes"


def test_sample_providers_yaml_is_valid(tmp_path: Path) -> None:
    """The bundled config/providers.yaml sample file must pass schema validation."""
    from pathlib import Path as P

    from app.config.loaders import load_providers_config

    sample_path = P(__file__).parent.parent / "config" / "providers.yaml"
    if not sample_path.exists():
        pytest.skip("config/providers.yaml not present")

    config = load_providers_config(sample_path)
    assert isinstance(config, AIProvidersConfig)
    # All routes in the sample should have valid step/provider
    for route in config.routes:
        assert route.step
        assert route.provider
    assert any(
        route.step == "draft_generate" and route.provider == "codex_wrapper"
        for route in config.routes
    )
