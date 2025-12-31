"""Fetch and detect plugin repository metadata from GitHub."""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

GITHUB_RAW_URL = "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
MARKETPLACE_JSON_PATH = ".claude-plugin/marketplace.json"

# Simple in-memory cache for marketplace data
# Key: "owner/repo/branch", Value: (FetchedRepoInfo, timestamp)
_marketplace_cache: "Dict[str, Tuple[Optional[FetchedRepoInfo], float]]" = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


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
    """Fetch a raw file from GitHub with retry logic.

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name
        path: File path within the repository

    Returns:
        File contents as string, or None if not found
    """
    import time
    import random

    url = GITHUB_RAW_URL.format(owner=owner, repo=repo, branch=branch, path=path)

    # Retry with exponential backoff (up to 3 attempts)
    max_retries = 3
    base_delay = 1.0
    timeout = 30  # Increased from 10 seconds

    for attempt in range(max_retries):
        try:
            request = Request(url)
            request.add_header("User-Agent", "code-assistant-manager")
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except HTTPError as e:
            if e.code == 404:
                logger.debug(f"File not found: {url}")
                return None
            else:
                logger.warning(f"HTTP error fetching {url} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return None
        except URLError as e:
            logger.warning(f"URL error fetching {url} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None
        except Exception as e:
            logger.warning(f"Error fetching {url} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None

        # Exponential backoff with jitter
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            logger.debug(f"Retrying in {delay:.1f} seconds...")
            time.sleep(delay)

    return None


def fetch_repo_info(
    owner: str, repo: str, branch: str = "main"
) -> Optional[FetchedRepoInfo]:
    """Fetch repository information from GitHub.

    Detects whether the repo is a marketplace (multiple plugins) or
    a single plugin repository.

    Uses caching to avoid repeated API calls.

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name (default: main)

    Returns:
        FetchedRepoInfo if successful, None otherwise
    """
    cache_key = f"{owner}/{repo}/{branch}"
    current_time = time.time()

    # Check cache first
    if cache_key in _marketplace_cache:
        cached_info, cache_timestamp = _marketplace_cache[cache_key]
        if current_time - cache_timestamp < _CACHE_TTL_SECONDS:
            logger.debug(f"Using cached data for {cache_key}")
            return cached_info
        else:
            # Cache expired, remove it
            del _marketplace_cache[cache_key]

    # Fetch fresh data
    # Try to fetch marketplace.json with multiple branch attempts
    content = None
    final_branch = branch

    # Common default branch names to try, in order of popularity
    branch_attempts = [branch]  # Start with requested branch
    if branch == "main":
        # If main was requested, also try master and other common branches
        branch_attempts.extend(["master", "develop", "development", "dev", "trunk"])
    elif branch == "master":
        # If master was requested, try main and other branches
        branch_attempts.extend(["main", "develop", "development", "dev", "trunk"])

    for attempt_branch in branch_attempts:
        content = fetch_raw_file(owner, repo, attempt_branch, MARKETPLACE_JSON_PATH)
        if content:
            final_branch = attempt_branch
            logger.debug(f"Found marketplace.json on branch '{final_branch}'")
            break

    if not content:
        logger.debug(f"Could not find {MARKETPLACE_JSON_PATH} in {owner}/{repo}")
        # Cache the None result to avoid repeated failed fetches
        _marketplace_cache[cache_key] = (None, current_time)
        return None

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in marketplace.json: {e}")
        # Cache the None result for invalid JSON too
        _marketplace_cache[cache_key] = (None, current_time)
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

    result = FetchedRepoInfo(
        owner=owner,
        repo=repo,
        branch=final_branch,
        name=name,
        description=description,
        type=repo_type,
        plugin_path=plugin_path,
        plugin_count=plugin_count,
        plugins=plugins,  # Always include plugins list for browse command
        version=version,
        homepage=homepage,
    )

    # Update cache with the final branch that was found
    final_cache_key = f"{owner}/{repo}/{final_branch}"
    _marketplace_cache[final_cache_key] = (result, current_time)
    return result


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
