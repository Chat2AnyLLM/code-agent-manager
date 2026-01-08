"""Agent manager for Code Assistant Manager.

This module provides the AgentManager class that orchestrates agent operations
across different AI tool handlers.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from ..repo_loader import RepoConfigLoader
from ..fetching.base import BaseEntityFetcher, RepoConfig
from .base import BaseAgentHandler
from .claude import ClaudeAgentHandler
from .codebuddy import CodebuddyAgentHandler
from .codex import CodexAgentHandler
from .copilot import CopilotAgentHandler
from .droid import DroidAgentHandler
from .gemini import GeminiAgentHandler
from .opencode import OpenCodeAgentHandler
from .models import Agent, AgentRepo
from ..fetcher import Fetcher

logger = logging.getLogger(__name__)


def _load_builtin_agent_repos() -> Dict:
    """Load built-in agent repos from the bundled agent_repos.json file.

    Returns bundled repos as a dictionary for fallback.
    """
    package_dir = Path(__file__).parent.parent
    repos_file = package_dir / "agent_repos.json"

    if repos_file.exists():
        try:
            with open(repos_file, "r", encoding="utf-8") as f:
                repos_data = json.load(f)
                return repos_data
        except Exception as e:
            logger.warning(f"Failed to load builtin agent repos: {e}")

    # Fallback defaults
    return {
        "iannuttall/claude-agents": {
            "owner": "iannuttall",
            "name": "claude-agents",
            "branch": "main",
            "enabled": True,
            "agentsPath": "agents",
        },
    }


def _load_agent_repos_from_config(config_dir: Optional[Path] = None) -> List[Dict]:
    """Load agent repos from config.yaml sources.

    Args:
        config_dir: Configuration directory

    Returns:
        List of repository configurations
    """
    loader = RepoConfigLoader(config_dir)
    bundled_fallback = _load_builtin_agent_repos()

    # Get repos from all configured sources
    repos_dict = loader.get_repos("agents", bundled_fallback)

    # Convert to list format for backward compatibility
    return [
        {
            "owner": repo.get("owner"),
            "name": repo.get("name"),
            "branch": repo.get("branch", "main"),
            "enabled": repo.get("enabled", True),
            "agentsPath": repo.get("agentsPath"),
            "exclude": repo.get("exclude"),
        }
        for repo in repos_dict.values()
    ]


DEFAULT_AGENT_REPOS = _load_agent_repos_from_config()

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

        # Initialize fetcher with agent parser
        from ..fetching.parsers import AgentParser
        self.fetcher = BaseEntityFetcher(parser=AgentParser())

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
        """Load agent repos from config sources (local + remote).
        
        Uses RepoConfigLoader to dynamically load from all configured sources,
        ensuring we always get the latest repository list from remote sources.
        """
        bundled_fallback = _load_builtin_agent_repos()
        repos_data_list = _load_agent_repos_from_config(self.config_dir)
        
        # Convert list format to dict format with AgentRepo objects
        repos = {}
        for repo_data in repos_data_list:
            repo = AgentRepo(
                owner=repo_data["owner"],
                name=repo_data["name"],
                branch=repo_data.get("branch", "main"),
                enabled=repo_data.get("enabled", True),
                agents_path=repo_data.get("agentsPath"),
                exclude=repo_data.get("exclude"),
            )
            repo_id = f"{repo.owner}/{repo.name}"
            repos[repo_id] = repo
        
        return repos

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
                exclude=repo_data.get("exclude"),
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

    def fetch_agents_from_repos(self, max_workers: int = 8) -> List[Agent]:
        """Fetch all agents from configured repositories in parallel.

        Args:
            max_workers: Maximum number of concurrent repository fetchers

        Returns:
            List of discovered agents
        """
        repos = self._load_repos()
        if not repos:
            self._init_default_repos_file()
            repos = self._load_repos()

        # Convert AgentRepo objects to RepoConfig objects for the fetcher
        repo_configs = [
            RepoConfig(
                owner=repo.owner,
                name=repo.name,
                branch=repo.branch,
                path=repo.agents_path,
                exclude=repo.exclude,
                enabled=repo.enabled
            )
            for repo in repos.values()
        ]

        # Fetch using unified fetcher
        agents = self.fetcher.fetch_from_repos(
            repos=repo_configs,
            max_workers=max_workers
        )

        # Update installed status from existing agents
        existing_agents = self._load_agents()
        for agent in agents:
            if agent.key in existing_agents:
                agent.installed = existing_agents[agent.key].installed
            existing_agents[agent.key] = agent

        # Save updated agents
        self._save_agents(existing_agents)

        logger.info(f"Total agents fetched: {len(agents)}")
        return agents

    def fetch_agents_from_external_sources(self) -> List[Agent]:
        """Fetch agents from external sources defined in agent_repos.json.

        This uses the same method as awesome-claude-agents for fetching from
        external JSON sources.

        Returns:
            List of discovered agents from all sources
        """
        # Load the agent_repos.json file
        package_dir = Path(__file__).parent.parent
        repos_file = package_dir / "agent_repos.json"

        if not repos_file.exists():
            logger.warning("agent_repos.json file not found")
            return []

        try:
            with open(repos_file, "r", encoding="utf-8") as f:
                repos_data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load agent_repos.json: {e}")
            return []

        # Use the Fetcher to get agents from each repository
        fetcher = Fetcher()
        all_agents = []
        existing_agents = self._load_agents()

        for repo_id, repo_data in repos_data.items():
            if not repo_data.get("enabled", True):
                logger.debug(f"Skipping disabled repository: {repo_id}")
                continue

            try:
                agents_data = fetcher.fetch_agents_from_repo(repo_data)
                for agent_data in agents_data:
                    # Convert to Agent model
                    filename = agent_data["file_path"].split("/")[-1] if "/" in agent_data["file_path"] else agent_data["file_path"]

                    agent_key = f"{repo_data['owner']}/{repo_data['name']}:{agent_data['name']}"

                    agent = Agent(
                        key=agent_key,
                        name=agent_data["name"],
                        description=agent_data["description"],
                        filename=filename,
                        installed=existing_agents.get(agent_key, Agent("", "", "", "", False)).installed,
                        repo_owner=repo_data["owner"],
                        repo_name=repo_data["name"],
                        repo_branch=repo_data.get("branch", "main"),
                        agents_path=repo_data.get("agentsPath", "agents"),
                        readme_url=f"https://github.com/{repo_data['owner']}/{repo_data['name']}/blob/{repo_data.get('branch', 'main')}/{agent_data['file_path']}",
                        tools=agent_data.get("source_data", {}).get("tools", []),
                        color=agent_data.get("source_data", {}).get("color"),
                    )
                    all_agents.append(agent)

                logger.info(f"Found {len(agents_data)} agents in {repo_id}")

            except Exception as e:
                logger.warning(f"Failed to fetch agents from {repo_id}: {e}")

        # Update existing agents database
        for agent in all_agents:
            existing_agents[agent.key] = agent
        self._save_agents(existing_agents)

        return all_agents

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
