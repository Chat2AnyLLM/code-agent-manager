"""Entity-specific parsers for skills, agents, and plugins."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from code_assistant_manager.fetching.base import EntityParser, RepoConfig
from code_assistant_manager.skills.models import Skill
from code_assistant_manager.agents.models import Agent

logger = logging.getLogger(__name__)


class SkillParser(EntityParser[Skill]):
    """Parser for skill entities."""

    def parse_from_file(
        self,
        file_path: Path,
        repo_config: RepoConfig
    ) -> Optional[Skill]:
        """Parse skill from SKILL.md file."""
        if file_path.name != "SKILL.md":
            return None

        skill_dir = file_path.parent

        # Parse metadata from SKILL.md
        meta = self._parse_metadata(file_path)

        # Calculate paths
        directory = skill_dir.name

        # Find the repo root by looking for .git directory
        repo_root = skill_dir
        for parent in skill_dir.parents:
            if (parent / '.git').exists():
                repo_root = parent
                break
        else:
            # Fallback to the original logic if .git not found
            repo_root = skill_dir.parents[-2]

        # Get relative path from repo root to skill directory
        try:
            source_directory = str(skill_dir.relative_to(repo_root))
        except ValueError:
            source_directory = directory

        # If skills_path is set, source_directory should be relative to skills_path
        if repo_config.path:
            skills_path = Path(repo_config.path)
            try:
                # Try to make source_directory relative to skills_path
                full_skills_path = repo_root / skills_path
                source_directory = str(skill_dir.relative_to(full_skills_path))
            except ValueError:
                # If we can't make it relative, keep the full path but warn
                logger.warning(f"Skill directory {skill_dir} is not under skills_path {repo_config.path}")

        # Create skill entity
        skill = Skill(
            key=self.create_entity_key(repo_config, directory),
            name=meta.get("name", directory),
            description=meta.get("description", ""),
            directory=directory,
            installed=False,
            repo_owner=repo_config.owner,
            repo_name=repo_config.name,
            repo_branch=repo_config.branch,
            skills_path=repo_config.path,
            readme_url=f"https://github.com/{repo_config.owner}/{repo_config.name}/tree/{repo_config.branch}/{source_directory}",
            source_directory=source_directory,
        )

        return skill

    def get_file_pattern(self) -> str:
        """Skills use SKILL.md files."""
        return "SKILL.md"

    def create_entity_key(self, repo_config: RepoConfig, entity_name: str) -> str:
        """Create skill key: owner/repo:directory."""
        return f"{repo_config.owner}/{repo_config.name}:{entity_name}"

    def _parse_metadata(self, skill_md: Path) -> dict:
        """Parse skill metadata from SKILL.md."""
        # This is a simplified version - in reality this would parse YAML frontmatter
        # from the existing handler logic
        meta = {"name": "", "description": ""}

        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple parsing - look for name and description
            lines = content.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if line.startswith('# '):
                    meta["name"] = line[2:].strip()
                elif line.startswith('description:') or line.startswith('Description:'):
                    meta["description"] = line.split(':', 1)[1].strip()
                    break
        except Exception as e:
            logger.warning(f"Failed to parse metadata from {skill_md}: {e}")

        return meta


class AgentParser(EntityParser[Agent]):
    """Parser for agent entities."""

    def parse_from_file(
        self,
        file_path: Path,
        repo_config: RepoConfig
    ) -> Optional[Agent]:
        """Parse agent from .md file."""
        if not file_path.suffix == ".md":
            return None

        # Parse markdown content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        agent_data = self._parse_markdown(content, file_path.name)

        if not agent_data:
            return None

        # Calculate relative path for readme_url
        try:
            # This assumes we know the relative path from repo root
            # May need adjustment based on actual usage
            relative_path = str(file_path.relative_to(file_path.parents[-2]))
        except (ValueError, IndexError):
            relative_path = file_path.name

        # Create agent entity
        agent = Agent(
            key=self.create_entity_key(repo_config, agent_data["name"]),
            name=agent_data["name"],
            description=agent_data["description"],
            filename=file_path.name,
            installed=False,
            repo_owner=repo_config.owner,
            repo_name=repo_config.name,
            repo_branch=repo_config.branch,
            agents_path=repo_config.path,
            readme_url=f"https://github.com/{repo_config.owner}/{repo_config.name}/blob/{repo_config.branch}/{relative_path}",
            tools=agent_data.get("tools", []),
            color=agent_data.get("color"),
        )

        return agent

    def get_file_pattern(self) -> str:
        """Agents use any .md files."""
        return "*.md"

    def create_entity_key(self, repo_config: RepoConfig, entity_name: str) -> str:
        """Create agent key: owner/repo:name."""
        return f"{repo_config.owner}/{repo_config.name}:{entity_name}"

    def _parse_markdown(self, content: str, filename: str) -> Optional[Dict[str, Any]]:
        """Parse agent data from markdown with YAML frontmatter."""
        # Simplified parsing - in reality this would parse YAML frontmatter
        # from the existing Fetcher logic
        try:
            lines = content.split('\n')
            frontmatter = []
            in_frontmatter = False

            for line in lines:
                if line.strip() == '---':
                    if not in_frontmatter:
                        in_frontmatter = True
                    else:
                        break
                elif in_frontmatter:
                    frontmatter.append(line)

            if not frontmatter:
                # No frontmatter, try to extract from content
                return self._parse_from_content(content, filename)

            # Parse frontmatter (simplified)
            agent_data = {}
            for line in frontmatter:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key == 'tools':
                        # Handle comma-separated values or arrays
                        value = value.strip()
                        if value.startswith('[') and value.endswith(']'):
                            # It's an array like ["tool1", "tool2"]
                            value = value[1:-1]  # Remove brackets
                        agent_data[key] = [t.strip().strip('"').strip("'") for t in value.split(',')]
                    else:
                        agent_data[key] = value

            # Ensure required fields
            if 'name' not in agent_data:
                agent_data['name'] = filename.replace('.md', '')

            if 'description' not in agent_data:
                agent_data['description'] = f"Agent: {agent_data['name']}"

            return agent_data

        except Exception as e:
            logger.warning(f"Failed to parse agent from markdown: {e}")
            return None

    def _parse_from_content(self, content: str, filename: str) -> Dict[str, Any]:
        """Fallback parsing when no frontmatter found."""
        # Extract name from first heading
        lines = content.split('\n')
        name = filename.replace('.md', '')

        for line in lines:
            if line.startswith('# '):
                name = line[2:].strip()
                break

        return {
            "name": name,
            "description": f"Agent: {name}",
            "tools": []
        }


class PluginParser(EntityParser[Dict[str, Any]]):
    """Parser for plugin marketplaces.

    Note: This returns plugin marketplace info, not individual Plugin models.
    The CLI layer handles converting this to individual plugins.
    """

    def parse_from_file(
        self,
        file_path: Path,
        repo_config: RepoConfig
    ) -> Optional[Dict[str, Any]]:
        """Parse marketplace.json for plugin metadata."""
        if file_path.name != "marketplace.json":
            return None

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to parse marketplace.json: {e}")
            return None

        # Return marketplace info with plugins
        return {
            "name": data.get("name", f"{repo_config.owner}/{repo_config.name}"),
            "description": data.get("description", ""),
            "plugins": data.get("plugins", []),
            "type": "marketplace",
            "owner": repo_config.owner,
            "repo": repo_config.name,
            "branch": repo_config.branch,
        }

    def get_file_pattern(self) -> str:
        """Plugins use marketplace.json in .claude-plugin/."""
        return ".claude-plugin/marketplace.json"

    def create_entity_key(self, repo_config: RepoConfig, entity_name: str) -> str:
        """Create plugin marketplace key."""
        return f"{repo_config.owner}/{repo_config.name}"