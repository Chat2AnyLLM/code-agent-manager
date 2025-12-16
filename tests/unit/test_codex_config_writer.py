from pathlib import Path

from code_assistant_manager.tools.config_writers.codex import upsert_codex_profile


def test_upsert_codex_profile_creates_and_is_idempotent(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    project_path = tmp_path / "proj"

    # Preserve unrelated content
    config_path.write_text("# header\n\n[unrelated]\nfoo = 1\n\n", encoding="utf-8")

    res1 = upsert_codex_profile(
        config_path=config_path,
        provider="copilot-api",
        base_url="https://10.0.0.1:5000",
        env_key="API_KEY_COPILOT",
        profile="grok-code-fast-1",
        model="grok-code-fast-1",
        reasoning_effort="low",
        project_path=project_path,
    )
    assert res1["changed"] is True
    assert res1["provider_existed"] is False
    assert res1["profile_existed"] is False

    text1 = config_path.read_text(encoding="utf-8")
    assert "[unrelated]" in text1
    assert "[model_providers.copilot-api]" in text1
    assert 'base_url = "https://10.0.0.1:5000"' in text1
    assert 'env_key = "API_KEY_COPILOT"' in text1
    assert "[profiles.grok-code-fast-1]" in text1
    assert 'model_provider = "copilot-api"' in text1
    assert f"[projects.\"{project_path}\"]" in text1

    # Second run with same values should not rewrite
    mtime_before = config_path.stat().st_mtime
    res2 = upsert_codex_profile(
        config_path=config_path,
        provider="copilot-api",
        base_url="https://10.0.0.1:5000",
        env_key="API_KEY_COPILOT",
        profile="grok-code-fast-1",
        model="grok-code-fast-1",
        reasoning_effort="low",
        project_path=project_path,
    )
    assert res2["changed"] is False
    assert res2["provider_existed"] is True
    assert res2["profile_existed"] is True
    assert config_path.stat().st_mtime == mtime_before
