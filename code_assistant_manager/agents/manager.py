"""Agent manager for Code Assistant Manager.

This module provides the AgentManager class that orchestrates agent operations
across different AI tool handlers.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import BaseAgentHandler
from .claude import ClaudeAgentHandler
from .codebuddy import CodebuddyAgentHandler
from .codex import CodexAgentHandler
from .copilot import CopilotAgentHandler
from .droid import DroidAgentHandler
from .gemini import GeminiAgentHandler
from .opencode import OpenCodeAgentHandler
from .models import Agent, AgentRepo

logger = logging.getLogger(__name__)


def _load_builtin_agent_repos() -> List[Dict]:
    """Load built-in agent repos from the bundled agent_repos.json file."""
    package_dir = Path(__file__).parent.parent
    repos_file = package_dir / "agent_repos.json"

    if repos_file.exists():
        try:
            with open(repos_file, "r", encoding="utf-8") as f:
                repos_data = json.load(f)
                return [
                    {
                        "owner": repo.get("owner"),
                        "name": repo.get("name"),
                        "branch": repo.get("branch", "main"),
                        "enabled": repo.get("enabled", True),
                        "agentsPath": repo.get("agentsPath"),
                    }
                    for repo in repos_data.values()
                ]
        except Exception as e:
            logger.warning(f"Failed to load builtin agent repos: {e}")

    # Fallback defaults
    return [
        {
            "owner": "iannuttall",
            "name": "claude-agents",
            "branch": "main",
            "enabled": True,
            "agentsPath": "agents",
        },
    ]


DEFAULT_AGENT_REPOS = _load_builtin_agent_repos()

# Registry of available handlers
AGENT_HANDLERS: Dict[str, Type[BaseAgentHandler]] = {
    "claude": ClaudeAgentHandler,
    "codex": CodexAgentHandler,
    "gemini": GeminiAgentHandler,
    "droid": DroidAgentHandler,
    "codebuddy": CodebuddyAgentHandler,
    "copilot": CopilotAgentHandler,
    "opencode": OpenCodeAgentHandler,
}

# Valid app types for agents
VALID_APP_TYPES = list(AGENT_HANDLERS.keys())


class AgentManager:
    """Manages agents storage, retrieval, and operations across different tools."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize agent manager.

        Args:
            config_dir: Configuration directory (defaults to ~/.config/code-assistant-manager)
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "code-assistant-manager"
        self.config_dir = Path(config_dir)
        self.agents_file = self.config_dir / "agents.json"
        self.repos_file = self.config_dir / "agent_repos.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize handlers
        self._handlers: Dict[str, BaseAgentHandler] = {}
        for app_name, handler_class in AGENT_HANDLERS.items():
            self._handlers[app_name] = handler_class()

    def get_handler(self, app_type: str) -> BaseAgentHandler:
        """Get the handler for a specific app type.

        Args:
            app_type: The app type (e.g., 'claude')

        Returns:
            The handler instance

        Raises:
            ValueError: If app_type is not supported
        """
        if app_type not in self._handlers:
            raise ValueError(
                f"Unknown app type: {app_type}. Supported: {list(self._handlers.keys())}"
            )
        return self._handlers[app_type]

    def _load_agents(self) -> Dict[str, Agent]:
        """Load agents from file."""
        if not self.agents_file.exists():
            return {}

        try:
            with open(self.agents_file, "r") as f:
                data = json.load(f)
            return {
                agent_key: Agent.from_dict(agent_data)
                for agent_key, agent_data in data.items()
            }
        except Exception as e:
            logger.warning(f"Failed to load agents: {e}")
            return {}

    def _save_agents(self, agents: Dict[str, Agent]) -> None:
        """Save agents to file."""
        try:
            data = {agent_key: agent.to_dict() for agent_key, agent in agents.items()}
            with open(self.agents_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(agents)} agents to {self.agents_file}")
        except Exception as e:
            logger.error(f"Failed to save agents: {e}")
            raise

    def _load_repos(self) -> Dict[str, AgentRepo]:
        """Load agent repos from file."""
        if not self.repos_file.exists():
            self._init_default_repos_file()

        try:
            with open(self.repos_file, "r") as f:
                data = json.load(f)
            return {
                repo_id: AgentRepo.from_dict(repo_data)
                for repo_id, repo_data in data.items()
            }
        except Exception as e:
            logger.warning(f"Failed to load agent repos: {e}")
            return {}

    def _init_default_repos_file(self) -> None:
        """Initialize the repos file with default agent repos."""
        repos = {}
        for repo_data in DEFAULT_AGENT_REPOS:
            repo = AgentRepo(
                owner=repo_data["owner"],
                name=repo_data["name"],
                branch=repo_data.get("branch", "main"),
                enabled=repo_data.get("enabled", True),
                agents_path=repo_data.get("agentsPath"),
            )
            repo_id = f"{repo.owner}/{repo.name}"
            repos[repo_id] = repo

        self._save_repos(repos)
        logger.info(f"Initialized {len(repos)} default agent repos")

    def _save_repos(self, repos: Dict[str, AgentRepo]) -> None:
        """Save agent repos to file."""
        try:
            data = {repo_id: repo.to_dict() for repo_id, repo in repos.items()}
            with open(self.repos_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(repos)} agent repos to {self.repos_file}")
        except Exception as e:
            logger.error(f"Failed to save agent repos: {e}")
            raise

    def get_all(self) -> Dict[str, Agent]:
        """Get all agents."""
        return self._load_agents()

    def get(self, agent_key: str) -> Optional[Agent]:
        """Get a specific agent."""
        agents = self._load_agents()
        return agents.get(agent_key)

    def get_repos(self) -> List[AgentRepo]:
        """Get all agent repos."""
        repos = self._load_repos()
        return list(repos.values())

    def add_repo(self, repo: AgentRepo) -> None:
        """Add an agent repo."""
        repos = self._load_repos()
        repo_id = f"{repo.owner}/{repo.name}"
        repos[repo_id] = repo
        self._save_repos(repos)
        logger.info(f"Added agent repo: {repo_id}")

    def remove_repo(self, owner: str, name: str) -> None:
        """Remove an agent repo."""
        repos = self._load_repos()
        repo_id = f"{owner}/{name}"
        if repo_id not in repos:
            raise ValueError(f"Agent repo '{repo_id}' not found")
        del repos[repo_id]
        self._save_repos(repos)
        logger.info(f"Removed agent repo: {repo_id}")

    def install(self, agent_key: str, app_type: str = "claude") -> Path:
        """Install an agent for a specific app.

        Args:
            agent_key: The agent identifier
            app_type: The app type to install to

        Returns:
            Path to the installed agent file
        """
        agents = self._load_agents()
        if agent_key not in agents:
            raise ValueError(f"Agent with key '{agent_key}' not found")

        agent = agents[agent_key]
        handler = self.get_handler(app_type)

        dest_path = handler.install(agent)

        # Update installed status
        agent.installed = True
        self._save_agents(agents)
        logger.info(f"Installed agent: {agent_key} to {app_type}")

        return dest_path

    def uninstall(self, agent_key: str, app_type: str = "claude") -> None:
        """Uninstall an agent from a specific app.

        Args:
            agent_key: The agent identifier
            app_type: The app type to uninstall from
        """
        agents = self._load_agents()
        if agent_key not in agents:
            raise ValueError(f"Agent with key '{agent_key}' not found")

        agent = agents[agent_key]
        handler = self.get_handler(app_type)

        handler.uninstall(agent)

        # Update installed status
        agent.installed = False
        self._save_agents(agents)
        logger.info(f"Uninstalled agent: {agent_key} from {app_type}")

    def fetch_agents_from_repos(self) -> List[Agent]:
        """Fetch all agents from configured repositories.

        Returns:
            List of discovered agents
        """
        repos = self._load_repos()
        if not repos:
            self._init_default_repos_file()
            repos = self._load_repos()

        all_agents = []
        existing_agents = self._load_agents()

        # Use claude handler for fetching (all repos use same format)
        handler = self.get_handler("claude")

        for repo_id, repo in repos.items():
            if not repo.enabled:
                logger.debug(f"Skipping disabled repo: {repo_id}")
                continue

            try:
                agents = self._fetch_agents_from_repo(repo, handler)
                for agent in agents:
                    if agent.key in existing_agents:
                        agent.installed = existing_agents[agent.key].installed
                    all_agents.append(agent)
                logger.info(f"Found {len(agents)} agents in {repo_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch agents from {repo_id}: {e}")

        # Merge and save
        for agent in all_agents:
            existing_agents[agent.key] = agent
        self._save_agents(existing_agents)

        return all_agents

    def _fetch_agents_from_repo(
        self, repo: AgentRepo, handler: BaseAgentHandler
    ) -> List[Agent]:
        """Fetch agents from a single repository.

        Args:
            repo: The repository to fetch from
            handler: The handler to use for parsing

        Returns:
            List of agents found
        """
        temp_dir, actual_branch = handler._download_repo(
            repo.owner, repo.name, repo.branch
        )
        agents = []

        try:
            scan_dir = temp_dir
            if repo.agents_path:
                scan_dir = temp_dir / repo.agents_path.strip("/")

            if not scan_dir.exists():
                logger.warning(f"Agents path not found: {scan_dir}")
                return agents

            for agent_file in scan_dir.glob("*.md"):
                if not agent_file.is_file():
                    continue

                # Skip README files
                if agent_file.name.lower() in ["readme.md", "contributing.md"]:
                    continue

                meta = handler.parse_agent_metadata(agent_file)
                filename = agent_file.name

                path_from_repo_root = agent_file.relative_to(temp_dir)
                readme_path = str(path_from_repo_root).replace("\\", "/")

                agent = Agent(
                    key=f"{repo.owner}/{repo.name}:{meta.get('name', filename.replace('.md', ''))}",
                    name=meta.get("name", filename.replace(".md", "")),
                    description=meta.get("description", ""),
                    filename=filename,
                    installed=False,
                    repo_owner=repo.owner,
                    repo_name=repo.name,
                    repo_branch=actual_branch,
                    agents_path=repo.agents_path,
                    readme_url=f"https://github.com/{repo.owner}/{repo.name}/blob/{actual_branch}/{readme_path}",
                    tools=meta.get("tools", []),
                    color=meta.get("color"),
                )
                agents.append(agent)
                logger.debug(f"Found agent: {agent.key}")
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

        return agents

    def sync_installed_status(self, app_type: str = "claude") -> None:
        """Sync the installed status of all agents.

        Args:
            app_type: The app type to check
        """
        handler = self.get_handler(app_type)
        installed_files = {f.name.lower() for f in handler.get_installed_files()}

        agents = self._load_agents()
        for agent in agents.values():
            agent.installed = agent.filename.lower() in installed_files
        self._save_agents(agents)
        logger.debug(f"Synced installed status for {len(agents)} agents")

    def get_installed_agents(self, app_type: str = "claude") -> List[Agent]:
        """Get all installed agents for a specific app.

        Args:
            app_type: The app type to check

        Returns:
            List of installed agents
        """
        handler = self.get_handler(app_type)
        installed_files = handler.get_installed_files()

        if not installed_files:
            return []

        installed_agents = []
        existing_agents = self._load_agents()

        for agent_file in installed_files:
            filename = agent_file.name

            # Find matching agent in database
            matching_agent = None
            for agent in existing_agents.values():
                if agent.filename.lower() == filename.lower():
                    matching_agent = agent
                    break

            if matching_agent:
                matching_agent.installed = True
                installed_agents.append(matching_agent)
            else:
                # Local agent not in database
                meta = handler.parse_agent_metadata(agent_file)
                agent = Agent(
                    key=f"local:{filename.replace('.md', '')}",
                    name=meta.get("name", filename.replace(".md", "")),
                    description=meta.get("description", ""),
                    filename=filename,
                    installed=True,
                    tools=meta.get("tools", []),
                    color=meta.get("color"),
                )
                installed_agents.append(agent)

        return installed_agents
