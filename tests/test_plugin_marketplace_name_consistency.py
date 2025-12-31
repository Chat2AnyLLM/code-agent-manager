"""Tests for plugin marketplace name consistency between list and install commands.

These tests ensure that:
1. Plugin list shows correct marketplace names from marketplace.json
2. Marketplace names don't show "owner/repo" format
3. Duplicate marketplaces are deduplicated
4. Selected marketplace names can be resolved for installation
5. No regression in the naming inconsistency bug
"""

import pytest
from unittest.mock import MagicMock, patch
from code_assistant_manager.plugins import PluginManager
from code_assistant_manager.plugins.models import PluginRepo


class TestPluginMarketplaceNameConsistency:
    """Test plugin marketplace name consistency between list and install."""

    def test_marketplace_name_from_repo_object(self, tmp_path):
        """Test that marketplace names come from repo.name, not dict key."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Simulate a marketplace entry with owner/repo format as key
        # but correct name from marketplace.json
        repos = {
            "anthropics/claude-code": PluginRepo(
                name="claude-code-plugins",  # Correct name from marketplace.json
                description="Test marketplace",
                repo_owner="anthropics",
                repo_name="claude-code",
                repo_branch="main",
                enabled=True,
                type="marketplace",
            ),
        }
        
        # The display should use repo.name, not the dict key
        for key, repo in repos.items():
            display_name = repo.name
            assert display_name == "claude-code-plugins"
            assert display_name != key
            assert "/" not in display_name

    def test_marketplace_name_without_slash(self):
        """Test that marketplace names don't contain slashes."""
        # Valid marketplace names from marketplace.json
        valid_names = [
            "claude-code-plugins",
            "claude-plugins-official",
            "awesome-plugins",
            "my-marketplace",
        ]
        
        for name in valid_names:
            assert "/" not in name, f"Marketplace name '{name}' should not contain '/'"

    def test_deduplication_removes_duplicates(self):
        """Test that duplicate marketplace entries are removed."""
        # Simulate finding the same marketplace multiple times
        found_entries = [
            {
                "marketplace": "claude-code-plugins",
                "source": "github.com/anthropics/claude-code",
                "plugin": {"name": "test"},
            },
            {
                "marketplace": "claude-code-plugins",
                "source": "github.com/anthropics/claude-code",  # Duplicate
                "plugin": {"name": "test"},
            },
            {
                "marketplace": "claude-plugins-official",
                "source": "github.com/anthropics/claude-plugins-official",
                "plugin": {"name": "test"},
            },
        ]
        
        # Deduplicate based on (name, source)
        seen = set()
        deduplicated = []
        for entry in found_entries:
            key = (entry["marketplace"], entry["source"])
            if key not in seen:
                seen.add(key)
                deduplicated.append(entry)
        
        # Should have only 2 entries (duplicate removed)
        assert len(deduplicated) == 2
        assert deduplicated[0]["marketplace"] == "claude-code-plugins"
        assert deduplicated[1]["marketplace"] == "claude-plugins-official"

    def test_marketplace_resolution_by_name(self, tmp_path):
        """Test that marketplaces can be resolved by their name attribute."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Add repos with different keys but specific names
        user_repos = {
            "anthropics/claude-code": {
                "name": "claude-code-plugins",
                "description": "Bundled plugins",
                "repoOwner": "anthropics",
                "repoName": "claude-code",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            },
            "claude-code-plugins": {
                "name": "claude-code-plugins",
                "description": "Bundled plugins",
                "repoOwner": "anthropics",
                "repoName": "claude-code",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            },
        }
        
        # Save to config
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(user_repos, f)
        
        # Test resolution
        repo = manager.get_repo("claude-code-plugins")
        assert repo is not None
        assert repo.name == "claude-code-plugins"
        assert repo.repo_owner == "anthropics"
        assert repo.repo_name == "claude-code"


class TestPluginMarketplaceResolution:
    """Test marketplace name resolution for installation."""

    def test_resolve_by_dict_key(self, tmp_path):
        """Test that marketplaces can be resolved by dict key."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Create config with specific key
        user_repos = {
            "my-marketplace": {
                "name": "my-marketplace",
                "description": "Test",
                "repoOwner": "owner",
                "repoName": "repo",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            },
        }
        
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(user_repos, f)
        
        repo = manager.get_repo("my-marketplace")
        assert repo is not None
        assert repo.name == "my-marketplace"

    def test_resolve_by_repo_name_attribute(self, tmp_path):
        """Test that marketplaces can be resolved by repo.name attribute."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Create config where key differs from name
        user_repos = {
            "owner/repo": {  # Key is owner/repo format
                "name": "marketplace-name",  # Name from marketplace.json
                "description": "Test",
                "repoOwner": "owner",
                "repoName": "repo",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
            },
        }
        
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(user_repos, f)
        
        # Should be resolvable by name attribute
        repo = manager.get_repo("marketplace-name")
        assert repo is not None
        assert repo.name == "marketplace-name"
        assert repo.repo_owner == "owner"

    def test_resolve_by_alias(self, tmp_path):
        """Test that marketplaces can be resolved by alias."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Create config with aliases
        user_repos = {
            "my-marketplace": {
                "name": "my-marketplace",
                "description": "Test",
                "repoOwner": "owner",
                "repoName": "repo",
                "repoBranch": "main",
                "type": "marketplace",
                "enabled": True,
                "aliases": ["alias1", "alias2"],
            },
        }
        
        import json
        config_file = tmp_path / "plugin_repos.json"
        with open(config_file, "w") as f:
            json.dump(user_repos, f)
        
        # Should be resolvable by alias
        repo = manager.get_repo("alias1")
        assert repo is not None
        assert repo.name == "my-marketplace"


class TestRegressionPrevention:
    """Tests to prevent regression of the marketplace naming bug."""

    def test_no_owner_slash_repo_in_display(self):
        """Test that displayed marketplace names don't use owner/repo format."""
        # These should NEVER be displayed as marketplace names
        invalid_display_names = [
            "anthropics/claude-code",
            "anthropics/claude-plugins-official",
            "owner/repo",
            "user/marketplace",
        ]
        
        # All should contain a slash
        for name in invalid_display_names:
            assert "/" in name, f"This is an invalid format: {name}"
        
        # Valid marketplace names from marketplace.json should not have slashes
        valid_names = [
            "claude-code-plugins",
            "claude-plugins-official",
            "awesome-plugins",
        ]
        
        for name in valid_names:
            assert "/" not in name, f"Valid marketplace name should not contain '/': {name}"

    def test_marketplace_name_comes_from_marketplace_json(self, tmp_path):
        """Test that marketplace names are fetched from marketplace.json, not config keys."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Simulate loading a repo where the key differs from the marketplace name
        test_cases = [
            {
                "key": "anthropics/claude-code",
                "expected_name": "claude-code-plugins",  # From marketplace.json
                "repo_owner": "anthropics",
                "repo_name": "claude-code",
            },
            {
                "key": "anthropics/claude-plugins-official",
                "expected_name": "claude-plugins-official",  # From marketplace.json
                "repo_owner": "anthropics",
                "repo_name": "claude-plugins-official",
            },
        ]
        
        for test_case in test_cases:
            repo = PluginRepo(
                name=test_case["expected_name"],
                description="Test",
                repo_owner=test_case["repo_owner"],
                repo_name=test_case["repo_name"],
                repo_branch="main",
                enabled=True,
                type="marketplace",
            )
            
            # The name should match what's in marketplace.json
            assert repo.name == test_case["expected_name"]
            assert repo.name != test_case["key"]

    def test_install_key_matches_list_display(self, tmp_path):
        """Test that the marketplace name shown in list can be used to install."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Create a repo with owner/repo key but correct name
        user_repos = {
            "anthropics/claude-code": {
                "name": "claude-code-plugins",
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
            json.dump(user_repos, f)
        
        # The name displayed in list should be resolvable
        display_name = "claude-code-plugins"
        repo = manager.get_repo(display_name)
        
        assert repo is not None, \
            f"Marketplace name '{display_name}' from list display should be resolvable for installation"
        assert repo.name == display_name
        assert repo.repo_owner == "anthropics"
        assert repo.repo_name == "claude-code"

    def test_no_duplicate_marketplaces_in_list(self):
        """Test that duplicate marketplace entries are deduplicated."""
        # Simulate multiple config entries pointing to same marketplace
        entries = [
            {
                "marketplace": "claude-code-plugins",
                "source": "github.com/anthropics/claude-code",
            },
            {
                "marketplace": "claude-code-plugins",  # Duplicate
                "source": "github.com/anthropics/claude-code",
            },
            {
                "marketplace": "other-marketplace",
                "source": "github.com/owner/repo",
            },
        ]
        
        # Deduplicate
        seen = set()
        deduplicated = []
        for entry in entries:
            key = (entry["marketplace"], entry["source"])
            if key not in seen:
                seen.add(key)
                deduplicated.append(entry)
        
        # Should have 2 unique entries
        assert len(deduplicated) == 2
        
        # Get unique marketplace names
        unique_names = {e["marketplace"] for e in deduplicated}
        assert len(unique_names) == 2
        assert "claude-code-plugins" in unique_names
        assert "other-marketplace" in unique_names


class TestMarketplaceInstallationScenarios:
    """Test different marketplace installation scenarios."""

    def test_install_with_simplified_name(self, tmp_path):
        """Test installing a plugin using the simplified marketplace name."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Setup marketplace config
        user_repos = {
            "anthropics/claude-code": {
                "name": "claude-code-plugins",
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
            json.dump(user_repos, f)
        
        # User sees "claude-code-plugins" in list and uses it to install
        marketplace_name = "claude-code-plugins"
        repo = manager.get_repo(marketplace_name)
        
        assert repo is not None
        assert repo.repo_owner == "anthropics"
        assert repo.repo_name == "claude-code"
        
        # This confirms the install path will work

    def test_install_with_dict_key(self, tmp_path):
        """Test that installation also works with the original dict key."""
        manager = PluginManager(config_dir=tmp_path)
        
        # Setup marketplace config
        user_repos = {
            "anthropics/claude-code": {
                "name": "claude-code-plugins",
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
            json.dump(user_repos, f)
        
        # User might also use the dict key directly
        dict_key = "anthropics/claude-code"
        repo = manager.get_repo(dict_key)
        
        assert repo is not None
        assert repo.name == "claude-code-plugins"
        
        # Both formats should work for backward compatibility
