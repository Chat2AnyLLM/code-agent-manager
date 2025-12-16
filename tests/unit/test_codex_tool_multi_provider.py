import os
from unittest.mock import MagicMock, patch

from code_assistant_manager.tools.codex import CodexTool


def test_codex_tool_multi_provider_prompts_each_provider_and_runs_selected_profile(monkeypatch):
    # Ensure we start with a clean env
    monkeypatch.delenv("KEY1", raising=False)
    monkeypatch.delenv("KEY2", raising=False)

    cfg = MagicMock()
    cfg.get_sections.return_value = ["ep1", "ep2"]

    def _get_ep_cfg(name: str):
        if name == "ep1":
            return {"api_key_env": "KEY1"}
        return {"api_key_env": "KEY2"}

    cfg.get_endpoint_config.side_effect = _get_ep_cfg

    tool = CodexTool(cfg)

    tool.endpoint_manager = MagicMock()
    tool.endpoint_manager._is_client_supported.return_value = True

    def _get_endpoint_config(name: str):
        if name == "ep1":
            return True, {"endpoint": "https://e1", "actual_api_key": "k1"}
        return True, {"endpoint": "https://e2", "actual_api_key": "k2"}

    tool.endpoint_manager.get_endpoint_config.side_effect = _get_endpoint_config

    def _fetch_models(name: str, endpoint_config, use_cache_if_available=False):
        if name == "ep1":
            return True, ["m1"]
        return True, ["m2"]

    tool.endpoint_manager.fetch_models.side_effect = _fetch_models

    # Don't touch the real filesystem
    with patch(
        "code_assistant_manager.tools.codex.upsert_codex_profile",
        return_value={
            "changed": True,
            "provider_existed": False,
            "profile_existed": False,
            "project_existed": False,
        },
    ):
        with patch.object(tool, "_ensure_tool_installed", return_value=True):
            # 1) pick model for ep1 (idx 0)
            # 2) pick model for ep2 (idx 0)
            # 3) pick profile to run => select second (idx 1) => m2
            menu_returns = [(True, 0), (True, 0), (True, 1)]

            with patch(
                "code_assistant_manager.menu.menus.display_centered_menu",
                side_effect=menu_returns,
            ):

                captured = {}

                def _run(cmd, env, *_args, **_kwargs):
                    captured["cmd"] = cmd
                    captured["env"] = env
                    return 0

                with patch.object(tool, "_run_tool_with_env", side_effect=_run):
                    rc = tool.run([])

    assert rc == 0
    assert captured["cmd"][:3] == ["codex", "-p", "m2"]
    assert captured["env"].get("KEY2") == "k2"
    assert "NODE_TLS_REJECT_UNAUTHORIZED" in captured["env"]
