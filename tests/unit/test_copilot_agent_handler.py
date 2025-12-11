from pathlib import Path

import pytest

from code_assistant_manager.agents.copilot import CopilotAgentHandler
from code_assistant_manager.agents.opencode import OpenCodeAgentHandler


def test_copilot_handler_properties(tmp_path):
    handler = CopilotAgentHandler(agents_dir_override=tmp_path)
    assert handler.app_name == "copilot"
    # When override supplied, agents_dir should match
    assert handler.agents_dir == tmp_path


def test_opencode_handler_properties(tmp_path):
    handler = OpenCodeAgentHandler(agents_dir_override=tmp_path)
    assert handler.app_name == "opencode"
    # When override supplied, agents_dir should match
    assert handler.agents_dir == tmp_path


def test_copilot_install_uninstall(tmp_path):
    # Create a fake agent markdown file in a temp repo layout
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    agent_md = repo_dir / "my-agent.md"
    agent_md.write_text(
        """---\nname: My Agent\ndescription: Test agent\n---\n# Agent"""
    )

    # Create an Agent-like object with required attributes
    class DummyAgent:
        def __init__(
            self, filename, repo_owner, repo_name, repo_branch=None, agents_path=None
        ):
            self.filename = filename
            self.repo_owner = repo_owner
            self.repo_name = repo_name
            self.repo_branch = repo_branch or "main"
            self.agents_path = agents_path

    # Monkeypatch BaseAgentHandler._download_repo by creating a handler with override
    handler = CopilotAgentHandler(agents_dir_override=tmp_path / "agents")

    # Patch _download_repo to return our repo_dir
    def fake_download(owner, name, branch):
        return repo_dir, branch

    handler._download_repo = fake_download

    dummy = DummyAgent("my-agent.md", "owner", "name")

    dest = handler.install(dummy)
    assert dest.exists()
    # Copilot agent profiles remain as .md files with normalized YAML frontmatter
    assert dest.name == "my-agent.md"


def test_opencode_install_uninstall(tmp_path):
    # Create a fake agent markdown file in a temp repo layout
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    agent_md = repo_dir / "my-agent.md"
    agent_md.write_text(
        """---\nname: My Agent\ndescription: Test agent\n---\n# Agent"""
    )

    # Create an Agent-like object with required attributes
    class DummyAgent:
        def __init__(
            self, filename, repo_owner, repo_name, repo_branch=None, agents_path=None
        ):
            self.filename = filename
            self.repo_owner = repo_owner
            self.repo_name = repo_name
            self.repo_branch = repo_branch or "main"
            self.agents_path = agents_path

    # Monkeypatch BaseAgentHandler._download_repo by creating a handler with override
    handler = OpenCodeAgentHandler(agents_dir_override=tmp_path / "agents")

    # Patch _download_repo to return our repo_dir
    def fake_download(owner, name, branch):
        return repo_dir, branch

    handler._download_repo = fake_download

    dummy = DummyAgent("my-agent.md", "owner", "name")

    dest = handler.install(dummy)
    assert dest.exists()
    # OpenCode agent profiles remain as .md files with normalized YAML frontmatter
    assert dest.name == "my-agent.md"

    # Now uninstall should remove the .md file
    removed = handler.uninstall(dummy)
    assert removed is True
    assert not dest.exists()
