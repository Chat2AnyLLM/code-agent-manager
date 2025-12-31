╔══════════════════════════════════════════════════════════════════════════════╗
║                   FETCH/PULL DUPLICATION ANALYSIS                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────┐
│ CURRENT STATE: ~500+ LINES OF DUPLICATED CODE                               │
└──────────────────────────────────────────────────────────────────────────────┘

┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  Subsystem   ┃    Lines    ┃  Parallel?  ┃         Fetch Method         ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Skills       │    153      │     ✓       │ fetch_skills_from_repos()    │
│ Agents       │    128      │     ✓       │ fetch_agents_from_repos()    │
│ Plugins      │    196      │     ✗       │ Sequential loop (CLI layer)  │
│              │             │             │ ⚠️  5-10× SLOWER!            │
└──────────────┴─────────────┴─────────────┴──────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ DUPLICATED PATTERNS                                                          │
└──────────────────────────────────────────────────────────────────────────────┘

✓ ThreadPoolExecutor setup (skills & agents)
✓ Thread-safe result collection with locks
✓ Git clone with branch fallback (main → master → develop)
✓ Temporary directory management
✓ File discovery patterns (rglob, walk)
✓ Entity model creation from parsed data
✓ State persistence (save to JSON)
✓ Error handling and logging

┌──────────────────────────────────────────────────────────────────────────────┐
│ PROPOSED SOLUTION: UNIFIED FETCHING FRAMEWORK                                │
└──────────────────────────────────────────────────────────────────────────────┘

New Module: code_assistant_manager/fetching/
├── base.py              # BaseEntityFetcher, EntityParser abstract classes
├── parallel.py          # ParallelFetcher with ThreadPoolExecutor
├── repository.py        # GitRepository with clone + branch fallback
├── parsers.py           # SkillParser, AgentParser, PluginParser
└── cache.py             # Unified caching layer

┌──────────────────────────────────────────────────────────────────────────────┐
│ EXPECTED BENEFITS                                                            │
└──────────────────────────────────────────────────────────────────────────────┘

📉 Code Reduction:      ~350 lines removed (70% reduction)
🔧 Maintainability:     Single source of truth for fetching
🧪 Testability:         Test once, use everywhere
🔌 Extensibility:       Easy to add new entity types
⚡ Performance (NEW):   Plugins 5-10× faster with parallelization

┌──────────────────────────────────────────────────────────────────────────────┐
│ PLUGIN PERFORMANCE IMPROVEMENT                                               │
└──────────────────────────────────────────────────────────────────────────────┘

                    BEFORE (Sequential)    │    AFTER (Parallel)
                  ─────────────────────────┼─────────────────────────
    1 repo              2s                 │         2s
    5 repos            10s                 │         2s  (5× faster!)
   10 repos            20s                 │         3s  (7× faster!)
   20 repos            40s                 │         5s  (8× faster!)

┌──────────────────────────────────────────────────────────────────────────────┐
│ IMPLEMENTATION ESTIMATE                                                      │
└──────────────────────────────────────────────────────────────────────────────┘

Phase 1: Fetching Module         2-3 hours
Phase 2: Parsers                  2-3 hours
Phase 3: Skills Refactor          1-2 hours
Phase 4: Agents Refactor          1-2 hours
Phase 5: Integration & Testing    1-2 hours
Phase 6: Deprecate Old Code       1 hour
Phase 7: Plugin Parallelization   2-3 hours  ⭐ High Impact!
                                 ───────────
Total:                           10-16 hours

┌──────────────────────────────────────────────────────────────────────────────┐
│ RECOMMENDATION                                                               │
└──────────────────────────────────────────────────────────────────────────────┘

🎯 HIGH PRIORITY: Implement this refactoring

Key Reasons:
1. Eliminates 70% of duplicated fetching code
2. Makes plugin fetching 5-10× faster (huge UX improvement)
3. Provides foundation for future entity types
4. Improves code quality and maintainability

Focus Areas:
• Phase 7 (Plugin parallelization) delivers the most user-visible impact
• Can be implemented incrementally (skills → agents → plugins)
• Low risk with proper testing


---

# Refactoring Plan: Reduce Duplication in Fetch/Pull Operations

## Executive Summary
The skill, agent, and plugin subsystems contain significant code duplication in their fetch/pull operations. This document proposes a refactoring to create a unified fetching framework that eliminates ~350+ lines of duplicated code.

**🔴 CRITICAL FINDING**: Plugins currently fetch repositories **sequentially** (no parallelization), making multi-repo operations very slow. The refactoring will add parallelization for a **5-10× performance improvement**.

## Current State Analysis

### Duplication Overview

All three subsystems (skills, agents, plugins) implement nearly identical fetching logic:

1. **Parallel Repository Processing**
2. **Git Clone/Download Operations**
3. **File Discovery & Parsing**
4. **Entity Model Creation**
5. **State Persistence**

### Current Implementations

#### 1. Skills Manager (`skills/manager.py`)
**Lines 338-491 (~153 lines)**

```python
def fetch_skills_from_repos(self, max_workers: int = 8) -> List[Skill]:
    """Fetch all skills from configured repositories in parallel."""
    repos = self._load_repos()
    enabled_repos = {k: v for k, v in repos.items() if v.enabled}
    
    # Thread-safe storage
    skills_results = []
    lock = threading.Lock()
    
    handler = self.get_handler("claude")
    
    def process_repository(repo_id: str, repo: SkillRepo):
        try:
            skills = self._fetch_skills_from_repo(repo, handler)
            # ... update installed status ...
            with lock:
                skills_results.extend(skills)
        except Exception as e:
            logger.warning(f"Failed to fetch skills from {repo_id}: {e}")
    
    # ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        future_to_repo = {
            executor.submit(process_repository, repo_id, repo): repo_id
            for repo_id, repo in enabled_repos.items()
        }
        # ... wait for completion ...
    
    # Merge and save
    for skill in all_skills:
        existing_skills[skill.key] = skill
    self._save_skills(existing_skills)
    
    return all_skills

def _fetch_skills_from_repo(self, repo: SkillRepo, handler) -> List[Skill]:
    """Fetch skills from a single repository."""
    temp_dir, actual_branch = handler._download_repo(repo.owner, repo.name, repo.branch)
    
    try:
        scan_dir = temp_dir
        if repo.skills_path:
            scan_dir = temp_dir / repo.skills_path.strip("/")
        
        # Scan for SKILL.md files recursively
        for skill_md in scan_dir.rglob("SKILL.md"):
            meta = handler.parse_skill_metadata(skill_md)
            skill = Skill(
                key=f"{repo.owner}/{repo.name}:{source_directory}",
                name=meta.get("name", directory),
                # ... more fields ...
            )
            skills.append(skill)
    finally:
        shutil.rmtree(temp_dir)
    
    return skills
```

#### 2. Agents Manager (`agents/manager.py`)
**Lines 300-428 (~128 lines)**

```python
def fetch_agents_from_repos(self, max_workers: int = 8) -> List[Agent]:
    """Fetch all agents from configured repositories in parallel."""
    repos = self._load_repos()
    enabled_repos = {k: v for k, v in repos.items() if v.enabled}
    
    # Thread-safe storage
    agents_results = []
    lock = threading.Lock()
    
    handler = self.get_handler("claude")
    
    def process_repository(repo_id: str, repo: AgentRepo):
        try:
            agents = self._fetch_agents_from_repo(repo, handler)
            # ... update installed status ...
            with lock:
                agents_results.extend(agents)
        except Exception as e:
            logger.warning(f"Failed to fetch agents from {repo_id}: {e}")
    
    # ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        future_to_repo = {
            executor.submit(process_repository, repo_id, repo): repo_id
            for repo_id, repo in enabled_repos.items()
        }
        # ... wait for completion ...
    
    # Merge and save
    for agent in all_agents:
        existing_agents[agent.key] = agent
    self._save_agents(existing_agents)
    
    return all_agents

def _fetch_agents_from_repo(self, repo: AgentRepo, handler) -> List[Agent]:
    """Fetch agents from a single repository."""
    fetcher = Fetcher()
    
    repo_data = {
        "owner": repo.owner,
        "name": repo.name,
        "branch": repo.branch,
        "agentsPath": repo.agents_path or "agents"
    }
    
    agents_data = fetcher.fetch_agents_from_repo(repo_data)
    
    for agent_data in agents_data:
        agent = Agent(
            key=f"{repo.owner}/{repo.name}:{agent_data['name']}",
            name=agent_data["name"],
            # ... more fields ...
        )
        agents.append(agent)
    
    return agents
```

#### 3. Plugins (`plugins/fetch.py` + CLI usage)
**Lines 128-229 in fetch.py (~101 lines) + Lines 223-318 in CLI (~95 lines) = ~196 lines**

**Plugin Fetch Architecture:**
Unlike skills and agents, plugins don't have a manager-level `fetch_*_from_repos()` method. Instead:
- `fetch_repo_info()` fetches metadata from single repo (no parallelization)
- CLI layer (`_show_available_plugins()`) iterates repos sequentially
- Each repo fetch is independent (no thread pool)

```python
# plugins/fetch.py - Single repo fetch
def fetch_repo_info(owner: str, repo: str, branch: str = "main") -> Optional[FetchedRepoInfo]:
    """Fetch repository information from GitHub."""
    # Check cache first
    cache_key = f"{owner}/{repo}/{branch}"
    if cache_key in _marketplace_cache:
        cached_info, cache_timestamp = _marketplace_cache[cache_key]
        if current_time - cache_timestamp < _CACHE_TTL_SECONDS:
            return cached_info
    
    # Try to fetch marketplace.json with multiple branch attempts
    branch_attempts = [branch, "master", "develop", "development", "dev", "trunk"]
    
    for attempt_branch in branch_attempts:
        content = fetch_raw_file(owner, repo, attempt_branch, MARKETPLACE_JSON_PATH)
        if content:
            final_branch = attempt_branch
            break
    
    # Parse JSON and create FetchedRepoInfo
    data = json.loads(content)
    plugins = data.get("plugins", [])
    
    result = FetchedRepoInfo(
        owner=owner,
        repo=repo,
        branch=final_branch,
        name=name,
        # ... more fields ...
    )
    
    # Update cache
    _marketplace_cache[final_cache_key] = (result, current_time)
    return result

# CLI layer - Sequential iteration (NO PARALLELIZATION)
def _show_available_plugins(manager: PluginManager, ...):
    """Show available plugins from all configured marketplaces."""
    all_repos = manager.get_all_repos()
    all_plugins = []
    
    for repo_name, repo in all_repos.items():  # Sequential!
        # Fetch repo info (blocking call)
        info = fetch_repo_info(
            repo.repo_owner, repo.repo_name, repo.repo_branch or "main"
        )
        if not info:
            continue
        
        if info.type == "marketplace":
            all_plugins.extend(info.plugins)
        else:
            all_plugins.append({...})  # Single plugin
    
    # Display plugins...
```

### Duplication Pattern Summary

| Feature | Skills | Agents | Plugins |
|---------|--------|--------|---------|
| **Parallel Processing** | ✓ ThreadPoolExecutor (lines 394-408) | ✓ ThreadPoolExecutor (lines 356-370) | ✗ Sequential loop (CLI layer) |
| **Thread-safe Results** | ✓ Lock + list (lines 368, 382) | ✓ Lock + list (lines 330, 344) | N/A |
| **Git Clone/Download** | ✓ handler._download_repo (line 432) | ✓ Fetcher.fetch_agents (line 404) | ✓ fetch_raw_file (HTTP only) |
| **Branch Fallback** | ✓ In handler | ✓ In Fetcher (lines 141-152) | ✓ branch_attempts (lines 166-178) |
| **File Discovery** | ✓ rglob("SKILL.md") (line 447) | ✓ os.walk for .md files | ✓ Fetch marketplace.json |
| **Caching** | ✗ No cache | ✗ No cache | ✓ In-memory cache (lines 149-157) |
| **Error Handling** | ✓ Try/catch with warning | ✓ Try/catch with warning | ✓ Try/catch with warning |
| **State Persistence** | ✓ _save_skills (line 415) | ✓ _save_agents (line 377) | ✓ Cache only (no persistence) |
| **Batch Fetching** | ✓ fetch_skills_from_repos() | ✓ fetch_agents_from_repos() | ✗ No batch method |

**Total Duplicated Lines: ~500+** (including plugin CLI sequential iteration)

## Proposed Solution

### Architecture: Unified Entity Fetcher

Create a generic fetching framework that handles all three entity types through polymorphism:

```
code_assistant_manager/
├── fetching/
│   ├── __init__.py
│   ├── base.py              # Base fetcher class
│   ├── parallel.py          # Parallel processing utilities
│   ├── repository.py        # Git operations (clone, download, cache)
│   ├── parsers.py           # Entity-specific parsers
│   └── cache.py             # Unified caching layer
```

### Phase 1: Create Base Fetcher Framework

**File: `code_assistant_manager/fetching/base.py`**

```python
"""Base fetching framework for skills, agents, and plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

# Generic type for entity (Skill, Agent, Plugin, etc.)
T = TypeVar('T')

@dataclass
class RepoConfig:
    """Generic repository configuration."""
    owner: str
    name: str
    branch: str = "main"
    path: Optional[str] = None  # Subdirectory path (skills_path, agents_path, etc.)
    enabled: bool = True


class EntityParser(ABC, Generic[T]):
    """Abstract parser for converting raw data to entities."""
    
    @abstractmethod
    def parse_from_file(
        self, 
        file_path: Path, 
        repo_config: RepoConfig
    ) -> Optional[T]:
        """Parse entity from a file.
        
        Args:
            file_path: Path to the file to parse
            repo_config: Repository configuration
            
        Returns:
            Parsed entity or None if invalid
        """
        pass
    
    @abstractmethod
    def get_file_pattern(self) -> str:
        """Get glob pattern for entity files (e.g., 'SKILL.md', '*.md')."""
        pass
    
    @abstractmethod
    def create_entity_key(self, repo_config: RepoConfig, entity_name: str) -> str:
        """Create unique key for entity."""
        pass


class BaseEntityFetcher(ABC, Generic[T]):
    """Base class for fetching entities from repositories.
    
    This provides a unified interface for fetching skills, agents, plugins, etc.
    """
    
    def __init__(self, parser: EntityParser[T], cache_ttl: int = 3600):
        """Initialize fetcher.
        
        Args:
            parser: Parser for converting files to entities
            cache_ttl: Cache time-to-live in seconds
        """
        self.parser = parser
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}
    
    def fetch_from_repos(
        self,
        repos: List[RepoConfig],
        max_workers: int = 8,
        use_cache: bool = True
    ) -> List[T]:
        """Fetch entities from multiple repositories in parallel.
        
        Args:
            repos: List of repository configurations
            max_workers: Maximum number of concurrent fetchers
            use_cache: Whether to use caching
            
        Returns:
            List of discovered entities
        """
        from code_assistant_manager.fetching.parallel import ParallelFetcher
        
        # Filter enabled repos
        enabled_repos = [r for r in repos if r.enabled]
        
        if not enabled_repos:
            logger.warning("No enabled repositories found")
            return []
        
        logger.info(f"Fetching from {len(enabled_repos)} repositories in parallel")
        
        # Use parallel fetcher
        parallel_fetcher = ParallelFetcher(
            fetcher_func=self._fetch_from_single_repo,
            max_workers=max_workers
        )
        
        results = parallel_fetcher.fetch_all(enabled_repos)
        
        # Flatten results
        all_entities = []
        for entities in results:
            all_entities.extend(entities)
        
        logger.info(f"Total entities fetched: {len(all_entities)}")
        return all_entities
    
    def _fetch_from_single_repo(self, repo: RepoConfig) -> List[T]:
        """Fetch entities from a single repository.
        
        Args:
            repo: Repository configuration
            
        Returns:
            List of entities found in the repository
        """
        from code_assistant_manager.fetching.repository import GitRepository
        
        git_repo = GitRepository(
            owner=repo.owner,
            name=repo.name,
            branch=repo.branch
        )
        
        entities = []
        
        try:
            # Clone/download repository
            with git_repo.clone() as temp_dir:
                # Determine scan directory
                scan_dir = temp_dir
                if repo.path:
                    scan_dir = temp_dir / repo.path.strip("/")
                
                if not scan_dir.exists():
                    logger.warning(f"Path not found: {scan_dir}")
                    return entities
                
                # Find entity files
                file_pattern = self.parser.get_file_pattern()
                for entity_file in scan_dir.rglob(file_pattern):
                    try:
                        entity = self.parser.parse_from_file(entity_file, repo)
                        if entity:
                            entities.append(entity)
                            logger.debug(f"Found entity: {entity}")
                    except Exception as e:
                        logger.warning(f"Failed to parse {entity_file}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to fetch from {repo.owner}/{repo.name}: {e}")
        
        return entities
```

### Phase 2: Parallel Processing Utilities

**File: `code_assistant_manager/fetching/parallel.py`**

```python
"""Parallel processing utilities for repository fetching."""

import concurrent.futures
import logging
import threading
from typing import Callable, List, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class ParallelFetcher:
    """Generic parallel fetcher using ThreadPoolExecutor."""
    
    def __init__(
        self,
        fetcher_func: Callable[[T], R],
        max_workers: int = 8
    ):
        """Initialize parallel fetcher.
        
        Args:
            fetcher_func: Function to fetch from single source
            max_workers: Maximum concurrent workers
        """
        self.fetcher_func = fetcher_func
        self.max_workers = max_workers
        self.results: List[R] = []
        self.lock = threading.Lock()
    
    def fetch_all(self, sources: List[T]) -> List[R]:
        """Fetch from all sources in parallel.
        
        Args:
            sources: List of sources to fetch from
            
        Returns:
            List of results from all sources
        """
        if not sources:
            return []
        
        actual_workers = min(self.max_workers, len(sources))
        logger.debug(f"Using {actual_workers} concurrent workers")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
            # Submit all tasks
            future_to_source = {
                executor.submit(self._fetch_safe, source): source
                for source in sources
            }
            
            # Wait for completion
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    result = future.result()
                    if result:
                        with self.lock:
                            self.results.append(result)
                except Exception as e:
                    logger.error(f"Exception fetching from {source}: {e}")
        
        return self.results
    
    def _fetch_safe(self, source: T) -> R:
        """Safely fetch from source with error handling."""
        try:
            return self.fetcher_func(source)
        except Exception as e:
            logger.warning(f"Failed to fetch from {source}: {e}")
            return None
```

### Phase 3: Repository Operations

**File: `code_assistant_manager/fetching/repository.py`**

```python
"""Git repository operations with caching."""

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Tuple
import logging

logger = logging.getLogger(__name__)


class GitRepository:
    """Git repository downloader with branch fallback."""
    
    BRANCH_FALLBACKS = ["main", "master", "develop", "development", "dev", "trunk"]
    
    def __init__(self, owner: str, name: str, branch: str = "main"):
        """Initialize git repository.
        
        Args:
            owner: Repository owner
            name: Repository name
            branch: Branch to clone (with automatic fallback)
        """
        self.owner = owner
        self.name = name
        self.branch = branch
        self.url = f"https://github.com/{owner}/{name}.git"
    
    @contextmanager
    def clone(self) -> Generator[Tuple[Path, str], None, None]:
        """Clone repository to temporary directory.
        
        Yields:
            Tuple of (temp_dir, actual_branch)
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=f"cam_{self.name}_"))
        actual_branch = self.branch
        
        try:
            # Try requested branch first
            branches_to_try = [self.branch]
            
            # Add fallbacks if branch is common
            if self.branch in self.BRANCH_FALLBACKS:
                branches_to_try.extend([b for b in self.BRANCH_FALLBACKS if b != self.branch])
            
            success = False
            for branch in branches_to_try:
                try:
                    logger.info(f"Cloning {self.url} (branch: {branch})...")
                    subprocess.run(
                        ["git", "clone", "--depth", "1", "--branch", branch, self.url, str(temp_dir)],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    actual_branch = branch
                    success = True
                    logger.info(f"Successfully cloned {self.owner}/{self.name} on branch {branch}")
                    break
                except subprocess.CalledProcessError:
                    if branch == branches_to_try[-1]:
                        raise
                    logger.debug(f"Branch {branch} not found, trying next...")
            
            if not success:
                raise RuntimeError(f"Failed to clone repository from any branch")
            
            yield temp_dir, actual_branch
            
        finally:
            # Cleanup
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
```

### Phase 4: Entity-Specific Parsers

**File: `code_assistant_manager/fetching/parsers.py`**

```python
"""Entity-specific parsers for skills, agents, and plugins."""

from pathlib import Path
from typing import Optional
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
            readme_url=f"https://github.com/{repo_config.owner}/{repo_config.name}/tree/{repo_config.branch}/{directory}",
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
        # Implementation from existing handler
        meta = {"name": "", "description": ""}
        # ... parse logic ...
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
            readme_url=f"https://github.com/{repo_config.owner}/{repo_config.name}/blob/{repo_config.branch}/{file_path}",
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
    
    def _parse_markdown(self, content: str, filename: str) -> dict:
        """Parse agent data from markdown with YAML frontmatter."""
        # Implementation from existing Fetcher
        # ... parse logic ...
        return {}
```

### Phase 5: Refactor Managers to Use New Framework

**Skills Manager - After Refactoring:**

```python
from code_assistant_manager.fetching.base import BaseEntityFetcher, RepoConfig
from code_assistant_manager.fetching.parsers import SkillParser

class SkillManager:
    def __init__(self):
        self.fetcher = BaseEntityFetcher(parser=SkillParser())
    
    def fetch_skills_from_repos(self, max_workers: int = 8) -> List[Skill]:
        """Fetch all skills from configured repositories."""
        repos = self._load_repos()
        
        # Convert to RepoConfig objects
        repo_configs = [
            RepoConfig(
                owner=repo.owner,
                name=repo.name,
                branch=repo.branch,
                path=repo.skills_path,
                enabled=repo.enabled
            )
            for repo in repos.values()
        ]
        
        # Fetch using unified fetcher
        skills = self.fetcher.fetch_from_repos(
            repos=repo_configs,
            max_workers=max_workers
        )
        
        # Update installed status
        existing_skills = self._load_skills()
        for skill in skills:
            if skill.key in existing_skills:
                skill.installed = existing_skills[skill.key].installed
            existing_skills[skill.key] = skill
        
        # Save
        self._save_skills(existing_skills)
        
        return skills
```

**Agents Manager - After Refactoring:**

```python
from code_assistant_manager.fetching.base import BaseEntityFetcher, RepoConfig
from code_assistant_manager.fetching.parsers import AgentParser

class AgentManager:
    def __init__(self):
        self.fetcher = BaseEntityFetcher(parser=AgentParser())
    
    def fetch_agents_from_repos(self, max_workers: int = 8) -> List[Agent]:
        """Fetch all agents from configured repositories."""
        repos = self._load_repos()
        
        # Convert to RepoConfig objects
        repo_configs = [
            RepoConfig(
                owner=repo.owner,
                name=repo.name,
                branch=repo.branch,
                path=repo.agents_path,
                enabled=repo.enabled
            )
            for repo in repos.values()
        ]
        
        # Fetch using unified fetcher
        agents = self.fetcher.fetch_from_repos(
            repos=repo_configs,
            max_workers=max_workers
        )
        
        # Update installed status and save
        existing_agents = self._load_agents()
        for agent in agents:
            if agent.key in existing_agents:
                agent.installed = existing_agents[agent.key].installed
            existing_agents[agent.key] = agent
        
        self._save_agents(existing_agents)
        
        return agents
```

## Benefits

### Code Reduction
- **Before**: ~500+ lines of duplicated code across 3 subsystems
- **After**: ~150 lines of shared code + ~50 lines per subsystem
- **Net Reduction**: ~350 lines (~70% reduction)

### Maintainability
- **Single Source of Truth**: Parallel processing logic in one place
- **Consistent Behavior**: All subsystems use same fetching mechanism
- **Easier Testing**: Test fetching logic once, use everywhere

### Performance
- **Unified Caching**: Share cache across all entity types
- **Optimized Git Operations**: Reusable git clone logic
- **Better Resource Management**: Consistent cleanup and error handling

### Extensibility
- **Easy to Add New Entity Types**: Just create new parser
- **Plugin Architecture**: Parsers are pluggable
- **Future-Proof**: Easy to add features like progress bars, retry logic, etc.

## Implementation Strategy

### Step 1: Create Fetching Module (2-3 hours)
1. Create `code_assistant_manager/fetching/` directory
2. Implement `base.py` with abstract classes
3. Implement `parallel.py` with ThreadPoolExecutor wrapper
4. Implement `repository.py` with Git operations
5. Add unit tests for each module

### Step 2: Implement Parsers (2-3 hours)
1. Create `parsers.py` with SkillParser
2. Move existing parsing logic from handlers
3. Create AgentParser using existing Fetcher logic
4. Add tests for parsers

### Step 3: Refactor Skills Manager (1-2 hours)
1. Update SkillManager to use BaseEntityFetcher
2. Remove old _fetch_skills_from_repos logic
3. Test skill fetching functionality
4. Update related tests

### Step 4: Refactor Agents Manager (1-2 hours)
1. Update AgentManager to use BaseEntityFetcher
2. Remove old _fetch_agents_from_repo logic
3. Remove or refactor existing Fetcher class
4. Test agent fetching functionality
5. Update related tests

### Step 5: Integration & Testing (1-2 hours)
1. Run full integration tests
2. Performance comparison tests
3. Update documentation
4. Add migration guide

### Step 6: Deprecate Old Code (1 hour)
1. Remove duplicated code from managers
2. Remove old Fetcher class (if not used elsewhere)
3. Clean up imports

**Total Estimated Time: 8-13 hours**

## Risks & Mitigations

### Risk: Breaking Changes
**Mitigation**: 
- Keep public APIs identical
- Add integration tests before refactoring
- Gradual rollout (skills → agents → plugins)

### Risk: Performance Regression
**Mitigation**:
- Benchmark existing performance
- Add performance tests
- Monitor actual fetch times

### Risk: Complex Abstractions
**Mitigation**:
- Keep abstractions simple
- Comprehensive documentation
- Code examples in docstrings

### Risk: Missing Edge Cases
**Mitigation**:
- Extensive testing of edge cases
- Preserve existing error handling
- Add logging at each step

## Testing Plan

### Unit Tests
- `test_fetching/test_base.py`: Test BaseEntityFetcher
- `test_fetching/test_parallel.py`: Test ParallelFetcher
- `test_fetching/test_repository.py`: Test GitRepository
- `test_fetching/test_parsers.py`: Test SkillParser, AgentParser

### Integration Tests
- Test full fetch workflow for skills
- Test full fetch workflow for agents
- Test parallel processing with multiple repos
- Test error handling and recovery

### Regression Tests
- Compare output before/after refactoring
- Verify same skills/agents are discovered
- Verify performance is maintained or improved

### Performance Tests
- Benchmark fetch time for 10 repos
- Monitor memory usage during parallel fetch
- Test with slow/unavailable repositories

## Success Metrics

1. **Code Reduction**: Remove 350+ lines of duplicated code (70% reduction)
2. **Test Coverage**: Maintain or improve current coverage (>80%)
3. **Performance**: 
   - Skills/Agents: No regression in fetch times (±10%)
   - **Plugins: 5-10× speedup from parallelization** (sequential → parallel)
4. **Bugs**: No new bugs introduced
5. **Documentation**: Complete documentation for new modules

## Future Enhancements

### Phase 7: Add Plugin Parallel Fetching
**IMPORTANT**: Plugins currently fetch sequentially, which is slow. The unified framework will add parallelization:

```python
class PluginParser(EntityParser[Dict[str, Any]]):
    """Parser for plugin marketplaces (returns plugin dict, not Plugin model)."""
    
    def parse_from_file(self, file_path: Path, repo_config: RepoConfig) -> Optional[Dict[str, Any]]:
        """Parse marketplace.json for plugin metadata."""
        if file_path.name != "marketplace.json":
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Return marketplace info with plugins
        return {
            "name": data.get("name"),
            "plugins": data.get("plugins", []),
            "type": "marketplace"
        }
    
    def get_file_pattern(self) -> str:
        """Plugins use marketplace.json in .claude-plugin/."""
        return ".claude-plugin/marketplace.json"
```

**Then update CLI to use parallel fetcher:**
```python
def _show_available_plugins(manager: PluginManager, ...):
    """Show available plugins - NOW WITH PARALLELIZATION."""
    from code_assistant_manager.fetching.base import BaseEntityFetcher, RepoConfig
    from code_assistant_manager.fetching.parsers import PluginParser
    
    all_repos = manager.get_all_repos()
    
    # Convert to RepoConfig
    repo_configs = [
        RepoConfig(
            owner=repo.repo_owner,
            name=repo.repo_name,
            branch=repo.repo_branch or "main",
            path=".claude-plugin",  # Standard plugin path
            enabled=True
        )
        for repo in all_repos.values()
        if repo.repo_owner and repo.repo_name
    ]
    
    # Fetch in parallel (instead of sequential loop)
    fetcher = BaseEntityFetcher(parser=PluginParser())
    marketplace_infos = fetcher.fetch_from_repos(
        repos=repo_configs,
        max_workers=8
    )
    
    # Flatten plugins from all marketplaces
    all_plugins = []
    for info in marketplace_infos:
        for plugin in info.get("plugins", []):
            plugin["marketplace"] = info["name"]
            all_plugins.append(plugin)
    
    # Display...
```

**Performance Impact:**
- **Before**: Sequential fetching of N repos = N × fetch_time
- **After**: Parallel fetching = max(fetch_time) with 8 workers
- **Example**: 10 repos @ 2s each = 20s → 2s (10× faster!)

### Phase 8: Advanced Features (Future)
- **Progress Bars**: Show fetch progress in CLI
- **Smart Caching**: Disk-based cache with TTL
- **Incremental Updates**: Only fetch changed files
- **Rate Limiting**: Respect GitHub API limits
- **Webhooks**: Trigger auto-fetch on repo updates

## Conclusion

This refactoring will:
- **Eliminate** ~250+ lines of duplicated code
- **Improve** maintainability and testability
- **Enable** easy addition of new entity types
- **Maintain** existing functionality and performance

The investment of 8-13 hours will pay off in reduced maintenance burden and cleaner architecture.

## Key Insight: Plugin Performance Issue

### Current Problem
**Plugins fetch repositories SEQUENTIALLY**, not in parallel like skills and agents:

```python
# CLI: plugin_management_commands.py:237-246
for repo_name, repo in all_repos.items():  # ← Sequential loop!
    info = fetch_repo_info(...)  # ← Blocking HTTP call (~2s each)
    if not info:
        continue
    # Process plugins...
```

**Performance Impact:**
- 1 repo: 2 seconds
- 5 repos: 10 seconds (2s × 5)
- 10 repos: 20 seconds (2s × 10) 
- 20 repos: 40 seconds (2s × 20) ⚠️

### Proposed Solution
Use the same parallel fetching as skills/agents:

```python
# After refactoring - Parallel fetching
fetcher = BaseEntityFetcher(parser=PluginParser())
results = fetcher.fetch_from_repos(repos, max_workers=8)
```

**Performance After:**
- 1 repo: 2 seconds
- 5 repos: 2 seconds (parallel!)
- 10 repos: 3 seconds (2 batches of 8 + 2)
- 20 repos: 5 seconds (3 batches)

**Speedup: 5-10× for typical usage with 5-10 repositories**

### Why This Matters
Users often configure multiple plugin marketplaces:
- `awesome-claude-code-plugins`
- `awesome-ai-tools`
- `community-plugins`
- Custom marketplaces

Current sequential fetching makes `cam plugin list` frustratingly slow. The refactoring will make it nearly instant.

---

