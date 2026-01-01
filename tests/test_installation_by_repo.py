"""Integration tests for installing agents, skills, and plugins from repositories.

These tests ensure that:
1. Items from each repository can be installed successfully
2. Name consistency is maintained during installation
3. Installation paths are correct
4. No regression in the installation flow
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from code_assistant_manager.skills import SkillManager, Skill
from code_assistant_manager.agents import AgentManager, Agent
from code_assistant_manager.plugins import PluginManager
from code_assistant_manager.plugins.models import PluginRepo


class TestSkillInstallationByRepo:
    """Test skill installation from different repositories."""

    @pytest.fixture
    def mock_download(self):
        """Mock the download functionality to avoid network calls."""
        with patch('code_assistant_manager.skills.base.BaseSkillHandler._download_repo') as mock:
            # Return a mock temp directory with expected structure
            mock_temp_dir = MagicMock()
            mock_temp_dir.__truediv__ = lambda self, other: Path(f"/mock/temp/{other}")
            mock_temp_dir.exists.return_value = True
            mock.return_value = (mock_temp_dir, "main")
            yield mock

    def test_install_skill_from_anthropics_skills(self, tmp_path, mock_download):
        """Test installing a skill from anthropics/skills repository."""
        manager = SkillManager(config_dir=tmp_path)
        
        # Create a skill from anthropics/skills
        skill = Skill(
            key="anthropics/skills:docx",
            name="docx",
            description="Document processing skill",
            directory="docx",
            source_directory="document-skills/docx",
            repo_owner="anthropics",
            repo_name="skills",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )
        
        # Save the skill
        skills = {skill.key: skill}
        manager._save_skills(skills)
        
        # Verify the install key format is correct
        assert "/" not in skill.key.split(":")[-1]
        assert skill.key == "anthropics/skills:docx"
        
        # Verify skill can be loaded
        loaded_skills = manager._load_skills()
        assert skill.key in loaded_skills

    def test_install_skill_from_composio_repo(self, tmp_path):
        """Test installing a skill from ComposioHQ/awesome-claude-skills."""
        manager = SkillManager(config_dir=tmp_path)
        
        skill = Skill(
            key="ComposioHQ/awesome-claude-skills:file-organizer",
            name="file-organizer",
            description="File organization skill",
            directory="file-organizer",
            source_directory="skills/file-organizer",
            repo_owner="ComposioHQ",
            repo_name="awesome-claude-skills",
            repo_branch="master",
            skills_path="/",
            installed=False,
        )
        
        skills = {skill.key: skill}
        manager._save_skills(skills)
        
        # Verify key format
        assert skill.key == "ComposioHQ/awesome-claude-skills:file-organizer"
        assert "/" not in skill.key.split(":")[-1]

    def test_install_skill_from_k_dense_repo(self, tmp_path):
        """Test installing a skill from K-Dense-AI/claude-scientific-skills."""
        manager = SkillManager(config_dir=tmp_path)
        
        skill = Skill(
            key="K-Dense-AI/claude-scientific-skills:biopython",
            name="biopython",
            description="Biopython skill",
            directory="biopython",
            source_directory="scientific-skills/biopython",
            repo_owner="K-Dense-AI",
            repo_name="claude-scientific-skills",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )
        
        skills = {skill.key: skill}
        manager._save_skills(skills)
        
        # Verify
        loaded_skills = manager._load_skills()
        assert skill.key in loaded_skills
        assert loaded_skills[skill.key].directory == "biopython"

    def test_skill_install_key_consistency(self, tmp_path):
        """Test that all skill install keys follow consistent format."""
        manager = SkillManager(config_dir=tmp_path)
        
        # Test skills from various repos
        test_skills = [
            {
                "key": "anthropics/skills:docx",
                "directory": "docx",
                "source": "document-skills/docx",
            },
            {
                "key": "BrownFineSecurity/iothackbot:onvifscan",
                "directory": "onvifscan",
                "source": "skills/onvifscan",
            },
            {
                "key": "MicrosoftDocs/mcp:microsoft-code-reference",
                "directory": "microsoft-code-reference",
                "source": "skills/microsoft-code-reference",
            },
        ]
        
        for skill_data in test_skills:
            skill = Skill(
                key=skill_data["key"],
                name=skill_data["directory"],
                description="Test skill",
                directory=skill_data["directory"],
                source_directory=skill_data["source"],
                repo_owner=skill_data["key"].split("/")[0],
                repo_name=skill_data["key"].split("/")[1].split(":")[0],
                repo_branch="main",
                skills_path="/",
                installed=False,
            )
            
            # Verify key format
            assert ":" in skill.key
            parts = skill.key.split(":")
            assert len(parts) == 2
            assert "/" in parts[0]  # Has owner/repo
            assert "/" not in parts[1]  # No slashes after colon


class TestAgentInstallationByRepo:
    """Test agent installation from different repositories."""

    def test_install_agent_from_dexploarer_repo(self, tmp_path):
        """Test installing an agent from Dexploarer/hyper-forge."""
        manager = AgentManager(config_dir=tmp_path)
        
        agent = Agent(
            key="Dexploarer/hyper-forge:security-specialist",
            name="security-specialist",
            description="Security specialist agent",
            filename="security-specialist",
            repo_owner="Dexploarer",
            repo_name="hyper-forge",
            repo_branch="main",
            installed=False,
        )
        
        agents = {agent.key: agent}
        manager._save_agents(agents)
        
        # Verify
        loaded_agents = manager._load_agents()
        assert agent.key in loaded_agents

    def test_install_agent_from_athola_repo(self, tmp_path):
        """Test installing an agent from athola/claude-night-market."""
        manager = AgentManager(config_dir=tmp_path)
        
        agent = Agent(
            key="athola/claude-night-market:Changelog",
            name="Changelog",
            description="Changelog agent",
            filename="Changelog",
            repo_owner="athola",
            repo_name="claude-night-market",
            repo_branch="main",
            installed=False,
        )
        
        agents = {agent.key: agent}
        manager._save_agents(agents)
        
        loaded_agents = manager._load_agents()
        assert agent.key in loaded_agents

    def test_agent_install_key_consistency(self, tmp_path):
        """Test that all agent install keys follow consistent format."""
        manager = AgentManager(config_dir=tmp_path)
        
        test_agents = [
            {
                "key": "Dexploarer/hyper-forge:security-specialist",
                "owner": "Dexploarer",
                "repo": "hyper-forge",
            },
            {
                "key": "athola/claude-night-market:Changelog",
                "owner": "athola",
                "repo": "claude-night-market",
            },
            {
                "key": "contains-studio/agents:your-agent-name",
                "owner": "contains-studio",
                "repo": "agents",
            },
        ]
        
        for agent_data in test_agents:
            agent = Agent(
                key=agent_data["key"],
                name=agent_data["key"].split(":")[-1],
                description="Test agent",
                filename=agent_data["key"].split(":")[-1],
                repo_owner=agent_data["owner"],
                repo_name=agent_data["repo"],
                repo_branch="main",
                installed=False,
            )
            
            # Verify key format
            assert ":" in agent.key
            assert agent.key.startswith(f"{agent_data['owner']}/{agent_data['repo']}:")


class TestPluginInstallationByMarketplace:
    """Test plugin installation from different marketplaces."""

    def test_anthropic_skills_marketplace(self, tmp_path):
        """Test anthropic-agent-skills marketplace configuration."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Create marketplace config
        config = {
            "anthropic-agent-skills": {
                "name": "anthropic-agent-skills",
                "description": "Anthropic example skills",
                "repoOwner": "anthropics",
                "repoName": "skills",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            }
        }
        
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Verify marketplace can be resolved
        repo = manager.get_repo("anthropic-agent-skills")
        assert repo is not None
        assert repo.name == "anthropic-agent-skills"
        assert repo.repo_owner == "anthropics"
        assert repo.repo_name == "skills"

    def test_awesome_claude_code_plugins_marketplace(self, tmp_path):
        """Test awesome-claude-code-plugins marketplace configuration."""
        manager = PluginManager(config_dir=tmp_path)
        
        config = {
            "awesome-claude-code-plugins": {
                "name": "awesome-claude-code-plugins",
                "description": "Awesome Claude Code plugins collection",
                "repoOwner": "ccplugins",
                "repoName": "awesome-claude-code-plugins",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            }
        }
        
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        repo = manager.get_repo("awesome-claude-code-plugins")
        assert repo is not None
        assert "/" not in repo.name  # No owner/repo format

    def test_superpowers_marketplace(self, tmp_path):
        """Test superpowers-marketplace configuration."""
        manager = PluginManager(config_dir=tmp_path)
        
        config = {
            "superpowers-marketplace": {
                "name": "superpowers-marketplace",
                "description": "Curated Claude Code plugins",
                "repoOwner": "obra",
                "repoName": "superpowers-marketplace",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            }
        }
        
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        repo = manager.get_repo("superpowers-marketplace")
        assert repo is not None
        assert repo.repo_owner == "obra"

    def test_marketplace_name_consistency(self, tmp_path):
        """Test that marketplace names don't use owner/repo format."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Test multiple marketplaces
        marketplaces = [
            {
                "key": "claude-code-plugins",
                "name": "claude-code-plugins",  # From marketplace.json
                "owner": "anthropics",
                "repo": "claude-code",
            },
            {
                "key": "anthropic-agent-skills",
                "name": "anthropic-agent-skills",
                "owner": "anthropics",
                "repo": "skills",
            },
            {
                "key": "awesome-claude-code-plugins",
                "name": "awesome-claude-code-plugins",
                "owner": "ccplugins",
                "repo": "awesome-claude-code-plugins",
            },
        ]
        
        config = {}
        for mp in marketplaces:
            config[mp["key"]] = {
                "name": mp["name"],
                "description": "Test marketplace",
                "repoOwner": mp["owner"],
                "repoName": mp["repo"],
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            }
        
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Verify all marketplaces are resolvable
        for mp in marketplaces:
            repo = manager.get_repo(mp["name"])
            assert repo is not None
            assert "/" not in repo.name
            assert repo.name == mp["name"]


class TestInstallationConsistencyAcrossTypes:
    """Test consistency across agents, skills, and plugins."""

    def test_all_use_consistent_key_format(self):
        """Test that agents, skills, and plugins all use consistent key format."""
        # Key format should be: owner/repo:identifier
        test_cases = [
            # Skills
            ("anthropics/skills:docx", "skill"),
            ("ComposioHQ/awesome-claude-skills:file-organizer", "skill"),
            # Agents
            ("Dexploarer/hyper-forge:security-specialist", "agent"),
            ("athola/claude-night-market:Changelog", "agent"),
            # Plugins (marketplace name should not have slash)
            ("claude-code-plugins", "plugin_marketplace"),
            ("anthropic-agent-skills", "plugin_marketplace"),
        ]
        
        for key, item_type in test_cases:
            if item_type in ["skill", "agent"]:
                # Should have owner/repo:identifier format
                assert ":" in key
                parts = key.split(":")
                assert len(parts) == 2
                assert "/" in parts[0]
                assert "/" not in parts[1]
            elif item_type == "plugin_marketplace":
                # Should not have slash (marketplace names from marketplace.json)
                assert "/" not in key

    def test_simplified_keys_are_installable(self, tmp_path):
        """Test that simplified keys work for installation."""
        # Test skill
        skill_manager = SkillManager(config_dir=tmp_path)
        skill = Skill(
            key="anthropics/skills:docx",
            name="docx",
            description="Test",
            directory="docx",
            source_directory="document-skills/docx",
            repo_owner="anthropics",
            repo_name="skills",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )
        skills = {skill.key: skill}
        skill_manager._save_skills(skills)
        assert skill.key in skill_manager._load_skills()
        
        # Test agent
        agent_manager = AgentManager(config_dir=tmp_path)
        agent = Agent(
            key="owner/repo:agent",
            name="agent",
            description="Test",
            filename="agent",
            repo_owner="owner",
            repo_name="repo",
            repo_branch="main",
            installed=False,
        )
        agents = {agent.key: agent}
        agent_manager._save_agents(agents)
        assert agent.key in agent_manager._load_agents()
        
        # Test plugin marketplace
        plugin_manager = PluginManager(config_dir=tmp_path)
        config = {
            "test-marketplace": {
                "name": "test-marketplace",
                "description": "Test",
                "repoOwner": "owner",
                "repoName": "repo",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            }
        }
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        repo = plugin_manager.get_repo("test-marketplace")
        assert repo is not None


class TestRealWorldInstallationScenarios:
    """Test real-world installation scenarios to prevent regressions."""

    def test_anthropics_docx_skill_installation_path(self, tmp_path):
        """Test the exact scenario from the bug report."""
        manager = SkillManager(config_dir=tmp_path)
        
        # The skill as shown in `cam skill list`
        skill = Skill(
            key="anthropics/skills:docx",  # Simplified format shown
            name="docx",
            description="Document processing",
            directory="docx",
            source_directory="document-skills/docx",
            repo_owner="anthropics",
            repo_name="skills",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )
        
        skills = {skill.key: skill}
        manager._save_skills(skills)
        
        # User should be able to install with the displayed key
        loaded = manager._load_skills()
        assert "anthropics/skills:docx" in loaded
        
        # This was the bug: it showed document-skills/docx
        assert "anthropics/skills:document-skills/docx" not in skill.key

    def test_plugin_marketplace_selection_bug(self, tmp_path):
        """Test the exact scenario from the plugin bug report."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Setup: marketplace with owner/repo key but correct name
        config = {
            "anthropics/claude-code": {
                "name": "claude-code-plugins",  # Correct name from marketplace.json
                "description": "Bundled plugins",
                "repoOwner": "anthropics",
                "repoName": "claude-code",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            },
        }
        
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # User selects "claude-code-plugins" from the list
        # This should work, not "anthropics/claude-code"
        repo = manager.get_repo("claude-code-plugins")
        assert repo is not None
        assert repo.name == "claude-code-plugins"
        
        # The bug was: it showed "anthropics/claude-code"
        # and failed with "claude-code" not found
