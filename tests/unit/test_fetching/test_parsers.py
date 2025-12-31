"""Unit tests for code_assistant_manager.fetching.parsers module."""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile

from code_assistant_manager.fetching.parsers import SkillParser, AgentParser, PluginParser
from code_assistant_manager.fetching.base import RepoConfig


class TestSkillParser(unittest.TestCase):
    """Test SkillParser class."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = SkillParser()

    def test_get_file_pattern(self):
        """Test get_file_pattern returns correct pattern."""
        self.assertEqual(self.parser.get_file_pattern(), "SKILL.md")

    def test_create_entity_key(self):
        """Test create_entity_key creates correct key format."""
        config = RepoConfig(owner="test-owner", name="test-repo")
        key = self.parser.create_entity_key(config, "test-skill")
        self.assertEqual(key, "test-owner/test-repo:test-skill")

    def test_parse_from_file_wrong_filename(self):
        """Test parse_from_file returns None for wrong filename."""
        config = RepoConfig(owner="test-owner", name="test-repo")

        with tempfile.TemporaryDirectory() as temp_dir:
            wrong_file = Path(temp_dir) / "WRONG.md"
            wrong_file.write_text("content")

            result = self.parser.parse_from_file(wrong_file, config)
            self.assertIsNone(result)

    def test_parse_from_file_skill_md(self):
        """Test parse_from_file with SKILL.md file."""
        config = RepoConfig(owner="test-owner", name="test-repo")

        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = Path(temp_dir) / "my-skill"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text("""# My Skill
description: A test skill
name: Custom Skill Name
""")

            skill = self.parser.parse_from_file(skill_md, config)

            self.assertIsNotNone(skill)
            self.assertEqual(skill.name, "My Skill")  # Parser takes first # header
            self.assertEqual(skill.description, "A test skill")
            self.assertEqual(skill.key, "test-owner/test-repo:my-skill")

    def test_parse_from_file_skill_md_minimal(self):
        """Test parse_from_file with minimal SKILL.md content."""
        config = RepoConfig(owner="test-owner", name="test-repo")

        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = Path(temp_dir) / "simple-skill"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text("# Simple Skill\nJust a basic skill.")

            skill = self.parser.parse_from_file(skill_md, config)

            self.assertIsNotNone(skill)
            self.assertEqual(skill.name, "Simple Skill")  # Parser takes first # header
            self.assertEqual(skill.description, "")  # No description found
            self.assertEqual(skill.key, "test-owner/test-repo:simple-skill")


class TestAgentParser(unittest.TestCase):
    """Test AgentParser class."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = AgentParser()

    def test_get_file_pattern(self):
        """Test get_file_pattern returns correct pattern."""
        self.assertEqual(self.parser.get_file_pattern(), "*.md")

    def test_create_entity_key(self):
        """Test create_entity_key creates correct key format."""
        config = RepoConfig(owner="test-owner", name="test-repo")
        key = self.parser.create_entity_key(config, "test-agent")
        self.assertEqual(key, "test-owner/test-repo:test-agent")

    def test_parse_from_file_wrong_extension(self):
        """Test parse_from_file returns None for non-md files."""
        config = RepoConfig(owner="test-owner", name="test-repo")

        with tempfile.TemporaryDirectory() as temp_dir:
            wrong_file = Path(temp_dir) / "agent.txt"
            wrong_file.write_text("content")

            result = self.parser.parse_from_file(wrong_file, config)
            self.assertIsNone(result)

    def test_parse_from_file_with_frontmatter(self):
        """Test parse_from_file with YAML frontmatter."""
        config = RepoConfig(owner="test-owner", name="test-repo")

        with tempfile.TemporaryDirectory() as temp_dir:
            agent_md = Path(temp_dir) / "test-agent.md"
            agent_md.write_text("""---
name: Test Agent
description: A test agent
tools: ["tool1", "tool2"]
color: blue
---

# Test Agent

This is a test agent.
""")

            agent = self.parser.parse_from_file(agent_md, config)

            self.assertIsNotNone(agent)
            self.assertEqual(agent.name, "Test Agent")
            self.assertEqual(agent.description, "A test agent")
            self.assertEqual(agent.tools, ["tool1", "tool2"])
            self.assertEqual(agent.color, "blue")
            self.assertEqual(agent.key, "test-owner/test-repo:Test Agent")

    def test_parse_from_file_without_frontmatter(self):
        """Test parse_from_file without YAML frontmatter."""
        config = RepoConfig(owner="test-owner", name="test-repo")

        with tempfile.TemporaryDirectory() as temp_dir:
            agent_md = Path(temp_dir) / "fallback-agent.md"
            agent_md.write_text("""# Fallback Agent

This agent has no frontmatter but should still be parsed.
""")

            agent = self.parser.parse_from_file(agent_md, config)

            self.assertIsNotNone(agent)
            self.assertEqual(agent.name, "Fallback Agent")  # Extracted from heading
            self.assertEqual(agent.description, "Agent: Fallback Agent")  # Fallback
            self.assertEqual(agent.tools, [])  # Empty tools
            self.assertEqual(agent.key, "test-owner/test-repo:Fallback Agent")


class TestPluginParser(unittest.TestCase):
    """Test PluginParser class."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = PluginParser()

    def test_get_file_pattern(self):
        """Test get_file_pattern returns correct pattern."""
        self.assertEqual(self.parser.get_file_pattern(), ".claude-plugin/marketplace.json")

    def test_create_entity_key(self):
        """Test create_entity_key creates correct key format."""
        config = RepoConfig(owner="test-owner", name="test-repo")
        key = self.parser.create_entity_key(config, "test-plugin")
        self.assertEqual(key, "test-owner/test-repo")

    def test_parse_from_file_wrong_filename(self):
        """Test parse_from_file returns None for wrong filename."""
        config = RepoConfig(owner="test-owner", name="test-repo")

        with tempfile.TemporaryDirectory() as temp_dir:
            wrong_file = Path(temp_dir) / "marketplace.txt"
            wrong_file.write_text("content")

            result = self.parser.parse_from_file(wrong_file, config)
            self.assertIsNone(result)

    def test_parse_from_file_marketplace_json(self):
        """Test parse_from_file with marketplace.json file."""
        config = RepoConfig(owner="test-owner", name="test-repo")

        with tempfile.TemporaryDirectory() as temp_dir:
            marketplace_json = Path(temp_dir) / ".claude-plugin" / "marketplace.json"
            marketplace_json.parent.mkdir(parents=True)
            marketplace_json.write_text("""{
  "name": "Test Marketplace",
  "description": "A test marketplace",
  "plugins": [
    {
      "name": "plugin1",
      "version": "1.0.0",
      "description": "First plugin"
    },
    {
      "name": "plugin2",
      "version": "2.0.0",
      "description": "Second plugin"
    }
  ]
}""")

            result = self.parser.parse_from_file(marketplace_json, config)

            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "Test Marketplace")
            self.assertEqual(result["description"], "A test marketplace")
            self.assertEqual(len(result["plugins"]), 2)
            self.assertEqual(result["owner"], "test-owner")
            self.assertEqual(result["repo"], "test-repo")
            self.assertEqual(result["branch"], "main")

    def test_parse_from_file_invalid_json(self):
        """Test parse_from_file with invalid JSON."""
        config = RepoConfig(owner="test-owner", name="test-repo")

        with tempfile.TemporaryDirectory() as temp_dir:
            marketplace_json = Path(temp_dir) / ".claude-plugin" / "marketplace.json"
            marketplace_json.parent.mkdir(parents=True)
            marketplace_json.write_text("invalid json content")

            result = self.parser.parse_from_file(marketplace_json, config)
            self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()