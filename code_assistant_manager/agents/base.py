"""Base class for app-specific agent handlers."""

import io
import logging
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from .models import Agent

logger = logging.getLogger(__name__)


class BaseAgentHandler(ABC):
    """Abstract base class for app-specific agent handlers.

    Each AI tool (Claude, etc.) can have its own implementation
    that defines how agents are stored and managed.
    """

    def __init__(
        self,
        agents_dir_override: Optional[Path] = None,
    ):
        """Initialize the handler with optional path overrides for testing.

        Args:
            agents_dir_override: Override the agents directory
        """
        self._agents_dir_override = agents_dir_override

    @property
    @abstractmethod
    def app_name(self) -> str:
        """Return the name of the app (e.g., 'claude')."""

    @property
    @abstractmethod
    def _default_agents_dir(self) -> Path:
        """Return the default agents directory for this app."""

    @property
    def agents_dir(self) -> Path:
        """Return the agents directory."""
        if self._agents_dir_override is not None:
            return self._agents_dir_override
        return self._default_agents_dir

    def install(self, agent: Agent) -> Path:
        """Install an agent by downloading and copying to the agents directory.

        Args:
            agent: The agent to install

        Returns:
            Path to the installed agent file

        Raises:
            ValueError: If agent has no repository information
        """
        if not agent.repo_owner or not agent.repo_name:
            raise ValueError(f"Agent '{agent.key}' has no repository information")

        # Ensure install directory exists
        self.agents_dir.mkdir(parents=True, exist_ok=True)

        # Download and install
        temp_dir, _ = self._download_repo(
            agent.repo_owner, agent.repo_name, agent.repo_branch or "main"
        )

        try:
            # Try to find the agent file using multiple strategies
            source_path = None
            
            # Strategy 1: Try exact path (agents_path + filename)
            if agent.agents_path:
                exact_path = temp_dir / agent.agents_path.strip("/") / agent.filename
                if exact_path.exists():
                    source_path = exact_path
                    logger.debug(f"Found agent at exact path: {exact_path}")
            
            # Strategy 2: Try root directory
            if not source_path:
                root_path = temp_dir / agent.filename
                if root_path.exists():
                    source_path = root_path
                    logger.debug(f"Found agent at root: {root_path}")
            
            # Strategy 3: Recursive search in agents_path directory
            if not source_path and agent.agents_path:
                search_dir = temp_dir / agent.agents_path.strip("/")
                if search_dir.exists():
                    source_path = self._find_file_recursive(search_dir, agent.filename)
                    if source_path:
                        logger.debug(f"Found agent via recursive search in {agent.agents_path}: {source_path}")
            
            # Strategy 4: Recursive search in plugins directory
            if not source_path:
                plugins_dir = temp_dir / "plugins"
                if plugins_dir.exists():
                    source_path = self._find_file_recursive(plugins_dir, agent.filename)
                    if source_path:
                        logger.debug(f"Found agent via recursive search in plugins: {source_path}")
            
            # Strategy 5: Recursive search in agents directory
            if not source_path:
                agents_dir = temp_dir / "agents"
                if agents_dir.exists():
                    source_path = self._find_file_recursive(agents_dir, agent.filename)
                    if source_path:
                        logger.debug(f"Found agent via recursive search in agents: {source_path}")
            
            # Strategy 6: Search entire repository
            if not source_path:
                source_path = self._find_file_recursive(temp_dir, agent.filename)
                if source_path:
                    logger.debug(f"Found agent via full repository search: {source_path}")
            
            if not source_path:
                raise ValueError(f"Agent file not found in repository: {agent.filename}")

            # Copy to install directory
            dest_path = self.agents_dir / agent.filename
            shutil.copy2(source_path, dest_path)
            logger.info(f"Installed agent to: {dest_path}")
            return dest_path
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _find_file_recursive(self, search_dir: Path, filename: str) -> Optional[Path]:
        """Recursively search for a file in a directory.
        
        Args:
            search_dir: Directory to search in
            filename: Filename to search for
            
        Returns:
            Path to the file if found, None otherwise
        """
        try:
            for item in search_dir.rglob(filename):
                if item.is_file():
                    return item
        except Exception as e:
            logger.debug(f"Error searching {search_dir}: {e}")
        return None


    def uninstall(self, agent: Agent) -> bool:
        """Uninstall an agent by removing its file.

        Args:
            agent: The agent to uninstall

        Returns:
            True if file was removed, False if it didn't exist
        """
        agent_file = self.agents_dir / agent.filename
        if agent_file.exists():
            agent_file.unlink()
            logger.info(f"Removed agent file: {agent_file}")
            return True
        return False

    def get_installed_files(self) -> List[Path]:
        """Get list of installed agent files.

        Returns:
            List of paths to installed agent markdown files
        """
        if not self.agents_dir.exists():
            return []
        return list(self.agents_dir.glob("*.md"))

    def is_installed(self, agent: Agent) -> bool:
        """Check if an agent is installed.

        Args:
            agent: The agent to check

        Returns:
            True if the agent file exists
        """
        agent_file = self.agents_dir / agent.filename
        return agent_file.exists()

    def parse_agent_metadata(self, agent_file: Path) -> Dict:
        """Parse agent metadata from markdown file with YAML front matter.

        Args:
            agent_file: Path to the agent markdown file

        Returns:
            Dictionary with name, description, tools, color
        """
        try:
            content = agent_file.read_text(encoding="utf-8")
            content = content.lstrip("\ufeff")  # Remove BOM

            parts = content.split("---", 2)
            if len(parts) >= 3:
                front_matter = parts[1].strip()

                # Try standard YAML parsing first
                meta = None
                try:
                    meta = yaml.safe_load(front_matter)
                except yaml.YAMLError:
                    # Fall back to simple line-by-line parsing
                    meta = self._parse_simple_yaml(front_matter)

                if isinstance(meta, dict):
                    # Parse tools as list
                    tools_raw = meta.get("tools", "")
                    if isinstance(tools_raw, str):
                        tools = [t.strip() for t in tools_raw.split(",") if t.strip()]
                    elif isinstance(tools_raw, list):
                        tools = tools_raw
                    else:
                        tools = []

                    # Truncate long descriptions
                    description = meta.get("description", "")
                    if description and len(description) > 200:
                        if ". " in description[:200]:
                            description = description[
                                : description.index(". ", 0, 200) + 1
                            ]
                        else:
                            description = description[:197] + "..."

                    return {
                        "name": meta.get("name"),
                        "description": description,
                        "tools": tools,
                        "color": meta.get("color"),
                    }
        except Exception as e:
            logger.debug(f"Failed to read agent file: {e}")

        return {}

    def _parse_simple_yaml(self, content: str) -> Dict:
        """Parse simple single-level YAML with key: value format.

        Handles cases where values contain unquoted colons.

        Args:
            content: YAML content string

        Returns:
            Dictionary of parsed values
        """
        result = {}
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            colon_idx = line.find(": ")
            if colon_idx > 0:
                key = line[:colon_idx].strip()
                value = line[colon_idx + 2 :].strip()
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                result[key] = value

        return result

    def _download_repo(
        self, owner: str, name: str, branch: str = "main"
    ) -> Tuple[Path, str]:
        """Download a GitHub repository as a zip file and extract it.

        Args:
            owner: Repository owner
            name: Repository name
            branch: Branch name

        Returns:
            Tuple of (Path to extracted directory, actual branch name used)
        """
        branches = [branch]
        if branch == "main":
            branches = ["main", "master"]
        elif branch == "master":
            branches = ["master", "main"]
        else:
            branches = [branch, "main", "master"]

        for try_branch in branches:
            url = (
                f"https://github.com/{owner}/{name}/archive/refs/heads/{try_branch}.zip"
            )
            logger.debug(f"Trying to download: {url}")

            try:
                req = Request(url, headers={"User-Agent": "code-assistant-manager"})
                with urlopen(req, timeout=60) as response:
                    zip_data = response.read()

                temp_dir = Path(tempfile.mkdtemp(prefix="cam-agent-"))

                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    root_dir = None
                    for name_in_zip in zf.namelist():
                        parts = name_in_zip.split("/")
                        if len(parts) > 1 and not root_dir:
                            root_dir = parts[0]

                        if root_dir and name_in_zip.startswith(root_dir + "/"):
                            rel_path = name_in_zip[len(root_dir) + 1 :]
                            if not rel_path:
                                continue

                            target_path = temp_dir / rel_path
                            if name_in_zip.endswith("/"):
                                target_path.mkdir(parents=True, exist_ok=True)
                            else:
                                target_path.parent.mkdir(parents=True, exist_ok=True)
                                with (
                                    zf.open(name_in_zip) as src,
                                    open(target_path, "wb") as dst,
                                ):
                                    dst.write(src.read())

                logger.info(f"Downloaded repository {owner}/{name}@{try_branch}")
                return temp_dir, try_branch

            except HTTPError as e:
                if e.code == 404:
                    logger.debug(f"Branch {try_branch} not found, trying next")
                    continue
                raise
            except URLError as e:
                logger.error(f"Failed to download repository: {e}")
                raise

        raise ValueError(f"Could not download repository {owner}/{name}")
