"""Helpers for writing OpenAI Codex config.toml without clobbering unrelated content."""

from __future__ import annotations

import re
from pathlib import Path


_BARE_KEY_RE = re.compile(r"[A-Za-z0-9_-]+\Z")


def _toml_quote_key(key: str) -> str:
    """Quote TOML key when it contains characters that would break dotted keys."""
    if _BARE_KEY_RE.fullmatch(key):
        return key
    escaped = key.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _upsert_table_block(toml_text: str, header_line: str, body_lines: list[str]) -> str:
    """Insert or replace a TOML table block starting at header_line."""
    block = "\n".join([header_line, *body_lines]).rstrip() + "\n\n"

    # Match the table header at start of line and replace until next table header.
    pattern = re.compile(
        rf"(?ms)^(?:{re.escape(header_line)})\n.*?(?=^\[|\Z)"
    )

    if pattern.search(toml_text):
        toml_text = pattern.sub(block, toml_text, count=1)
        return toml_text

    # Append.
    sep = "\n" if toml_text and not toml_text.endswith("\n") else ""
    return toml_text + sep + block


def upsert_codex_profile(
    *,
    config_path: Path,
    provider: str,
    base_url: str,
    env_key: str,
    profile: str,
    model: str,
    reasoning_effort: str = "low",
    project_path: Path | None = None,
) -> dict:
    """Upsert Codex model_provider, profile, and per-project trust config.

    Returns:
        Dict with keys: changed, provider_existed, profile_existed, project_existed
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""

    provider_key = _toml_quote_key(provider)
    profile_key = _toml_quote_key(profile)

    provider_header = f"[model_providers.{provider_key}]"
    profile_header = f"[profiles.{profile_key}]"

    provider_existed = bool(re.search(rf"(?m)^{re.escape(provider_header)}$", original))
    profile_existed = bool(re.search(rf"(?m)^{re.escape(profile_header)}$", original))

    project_existed = False
    project_header = None
    if project_path is not None:
        proj_key = _toml_quote_key(str(project_path))
        project_header = f"[projects.{proj_key}]"
        project_existed = bool(
            re.search(rf"(?m)^{re.escape(project_header)}$", original)
        )

    updated = original

    updated = _upsert_table_block(
        updated,
        provider_header,
        [
            f"name = \"{provider}\"",
            f"base_url = \"{base_url}\"",
            f"env_key = \"{env_key}\"",
        ],
    )

    updated = _upsert_table_block(
        updated,
        profile_header,
        [
            f"model = \"{model}\"",
            f"model_provider = \"{provider}\"",
            f"model_reasoning_effort = \"{reasoning_effort}\"",
        ],
    )

    if project_path is not None and project_header is not None:
        updated = _upsert_table_block(
            updated,
            project_header,
            ["trust_level = \"trusted\""],
        )

    changed = updated != original
    if changed:
        config_path.write_text(updated, encoding="utf-8")

    return {
        "changed": changed,
        "provider_existed": provider_existed,
        "profile_existed": profile_existed,
        "project_existed": project_existed,
    }
