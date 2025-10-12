"""Fetch and detect plugin repository metadata from GitHub."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

GITHUB_RAW_URL = "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
MARKETPLACE_JSON_PATH = ".claude-plugin/marketplace.json"


@dataclass
class FetchedRepoInfo:
    """Information fetched from a GitHub repository."""

    owner: str
    repo: str
    branch: str
    name: str
    description: str
    type: str  # "plugin" or "marketplace"
    plugin_path: Optional[str] = None
    plugin_count: int = 1
    plugins: Optional[List[Dict[str, Any]]] = None
    version: Optional[str] = None
    homepage: Optional[str] = None


def parse_github_url(url: str) -> Optional[Tuple[str, str, str]]:
    """Parse a GitHub URL or owner/repo string into (owner, repo, branch).

    Supports:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - github.com/owner/repo
        - owner/repo

    Returns:
        Tuple of (owner, repo, branch) or None if invalid
    """
    # Clean up the URL
    url = url.strip().rstrip("/")

    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]

    # Pattern for full GitHub URL
    github_pattern = r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+)"
    match = re.match(github_pattern, url)
    if match:
        return (match.group(1), match.group(2), "main")

    # Pattern for owner/repo format
    simple_pattern = r"^([^/]+)/([^/]+)$"
    match = re.match(simple_pattern, url)
    if match:
        return (match.group(1), match.group(2), "main")

    return None


def fetch_raw_file(owner: str, repo: str, branch: str, path: str) -> Optional[str]:
    """Fetch a raw file from GitHub.

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name
        path: File path within the repository

    Returns:
        File contents as string, or None if not found
    """
    url = GITHUB_RAW_URL.format(owner=owner, repo=repo, branch=branch, path=path)
    try:
        request = Request(url)
        request.add_header("User-Agent", "code-assistant-manager")
        with urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8")
    except HTTPError as e:
        if e.code == 404:
            logger.debug(f"File not found: {url}")
        else:
            logger.warning(f"HTTP error fetching {url}: {e}")
        return None
    except URLError as e:
        logger.warning(f"URL error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
        return None


def fetch_repo_info(
    owner: str, repo: str, branch: str = "main"
) -> Optional[FetchedRepoInfo]:
    """Fetch repository information from GitHub.

    Detects whether the repo is a marketplace (multiple plugins) or
    a single plugin repository.

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name (default: main)

    Returns:
        FetchedRepoInfo if successful, None otherwise
    """
    # Try to fetch marketplace.json
    content = fetch_raw_file(owner, repo, branch, MARKETPLACE_JSON_PATH)

    if not content:
        # Try 'master' branch if 'main' failed
        if branch == "main":
            content = fetch_raw_file(owner, repo, "master", MARKETPLACE_JSON_PATH)
            if content:
                branch = "master"

    if not content:
        logger.warning(f"Could not find {MARKETPLACE_JSON_PATH} in {owner}/{repo}")
        return None

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in marketplace.json: {e}")
        return None

    # Extract basic info
    name = data.get("name", repo)
    metadata = data.get("metadata", {})
    description = metadata.get("description", data.get("description", ""))
    version = metadata.get("version")
    homepage = metadata.get("homepage")
    plugin_root = metadata.get("pluginRoot", "./plugins")

    # Get plugins list
    plugins = data.get("plugins", [])
    plugin_count = len(plugins)

    # Determine type: if it has a marketplace.json with plugins array, it's a marketplace
    # Even single-plugin repos can be marketplaces if structured that way
    # The presence of marketplace.json indicates marketplace structure
    repo_type = "marketplace"
    plugin_path = None  # Marketplaces don't have a single plugin path

    return FetchedRepoInfo(
        owner=owner,
        repo=repo,
        branch=branch,
        name=name,
        description=description,
        type=repo_type,
        plugin_path=plugin_path,
        plugin_count=plugin_count,
        plugins=plugins,  # Always include plugins list for browse command
        version=version,
        homepage=homepage,
    )


def fetch_repo_info_from_url(url: str) -> Optional[FetchedRepoInfo]:
    """Fetch repository information from a GitHub URL.

    Args:
        url: GitHub URL or owner/repo string

    Returns:
        FetchedRepoInfo if successful, None otherwise
    """
    parsed = parse_github_url(url)
    if not parsed:
        logger.warning(f"Invalid GitHub URL: {url}")
        return None

    owner, repo, branch = parsed
    return fetch_repo_info(owner, repo, branch)
