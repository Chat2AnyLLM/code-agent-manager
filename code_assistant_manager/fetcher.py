#!/usr/bin/env python3
"""
HTTP fetching utilities for agent data
"""

import requests
import json
import logging
import time
import hashlib
import yaml
import subprocess
import tempfile
import shutil
import os
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class Fetcher:
    """HTTP data fetching utilities for agent repositories."""

    def __init__(self, timeout: int = 30, cache_ttl: int = 3600):
        self.timeout = timeout
        self.cache_ttl = cache_ttl  # Cache TTL in seconds (default 1 hour)
        self.session = requests.Session()
        self.cache: Dict[str, Dict[str, Any]] = {}  # URL -> {data, timestamp}

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid."""
        if 'timestamp' not in cache_entry:
            return False
        return (time.time() - cache_entry['timestamp']) < self.cache_ttl

    def _get_cached_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if valid."""
        cache_key = self._get_cache_key(url)
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry):
                logger.debug("Cache hit for: %s", url)
                return cache_entry['data']
            else:
                logger.debug("Cache expired for: %s", url)
                del self.cache[cache_key]
        return None

    def _set_cached_data(self, url: str, data: Dict[str, Any]):
        """Store data in cache."""
        cache_key = self._get_cache_key(url)
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }

    def fetch_json(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch JSON data from URL with caching and performance monitoring."""
        # Check cache first
        cached_data = self._get_cached_data(url)
        if cached_data is not None:
            return cached_data

        start_time = time.time()
        try:
            logger.info("Fetching data from: %s", url)
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            fetch_time = time.time() - start_time
            logger.info("Successfully fetched data from %s in %.2f seconds", url, fetch_time)

            # Cache the successful response
            self._set_cached_data(url, data)

            return data

        except requests.exceptions.RequestException as e:
            fetch_time = time.time() - start_time
            logger.error("Failed to fetch %s in %.2f seconds: %s", url, fetch_time, e)
            return None
        except json.JSONDecodeError as e:
            fetch_time = time.time() - start_time
            logger.error("Failed to parse JSON from %s in %.2f seconds: %s", url, fetch_time, e)
            return None

    def fetch_agent_repos_from_source(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch agent repository data from a configured source."""
        url = source_config.get("url")
        if not url:
            logger.error("No URL specified in source config")
            return []

        data = self.fetch_json(url)
        if not data:
            return []

        # The expected format is a dict with repo IDs as keys
        repos = []
        for repo_id, repo_data in data.items():
            if isinstance(repo_data, dict):
                repo_data["id"] = repo_id
                repo_data["source_url"] = url
                repos.append(repo_data)

        logger.info("Fetched %d agent repositories from %s", len(repos), url)
        return repos

    def fetch_agents_from_repo(self, repo_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch all agents from a repository using git clone."""
        agents = []

        repo_owner = repo_data.get("owner")
        repo_name = repo_data.get("name")
        repo_branch = repo_data.get("branch", "main")
        agents_path = repo_data.get("agentsPath", "agents")

        if not repo_owner or not repo_name:
            logger.warning("Missing repo information: %s", repo_data.get("id"))
            return agents

        repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                logger.info(f"Cloning repository {repo_url}...")
                # Clone with depth 1 to save time and space
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", repo_branch, repo_url, tmp_dir],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                # Try master if main fails, or vice versa
                alternative_branch = "master" if repo_branch == "main" else "main"
                try:
                    logger.info(f"Cloning failed for {repo_branch}, trying {alternative_branch}...")
                    subprocess.run(
                        ["git", "clone", "--depth", "1", "--branch", alternative_branch, repo_url, tmp_dir],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                except subprocess.CalledProcessError:
                    logger.error(f"Failed to clone repository {repo_url}: {e.stderr}")
                    return agents

            # Search for agent files in the specified path
            search_path = os.path.join(tmp_dir, agents_path)
            if not os.path.exists(search_path):
                logger.warning(f"Agents path {agents_path} not found in {repo_owner}/{repo_name}")
                return agents

            for root, _, files in os.walk(search_path):
                for filename in files:
                    if filename.endswith(".md"):
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, tmp_dir)

                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                markdown_content = f.read()

                            agent_data = self._parse_agent_markdown(markdown_content, filename)

                            if agent_data:
                                agent = {
                                    "name": agent_data.get("name", filename.replace('.md', '')),
                                    "description": agent_data.get("description", ""),
                                    "category": agent_data.get("category", "General"),
                                    "author": agent_data.get("author"),
                                    "version": agent_data.get("version", "1.0.0"),
                                    "repo_owner": repo_owner,
                                    "repo_name": repo_name,
                                    "repo_url": f"https://github.com/{repo_owner}/{repo_name}",
                                    "file_path": relative_path,
                                    "tags": agent_data.get("tags", []),
                                    "source_data": agent_data
                                }
                                agents.append(agent)
                        except Exception as e:
                            logger.warning(f"Failed to read or parse {file_path}: {e}")

        logger.info("Fetched %d agents from repository %s/%s", len(agents), repo_owner, repo_name)
        return agents

    def _parse_agent_markdown(self, content: str, filename: str) -> Optional[Dict[str, Any]]:
        """Parse agent data from markdown content, including YAML front matter."""
        try:
            agent_data = {
                'name': filename.replace('.md', '').replace('-', ' ').title(),
                'description': '',
                'category': 'General',
                'tags': [],
                'version': '1.0.0',
                'author': None
            }

            content_body = content

            # Check for YAML front matter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    front_matter = parts[1]
                    content_body = parts[2]

                    try:
                        metadata = yaml.safe_load(front_matter)
                        if isinstance(metadata, dict):
                            # Map metadata to agent_data
                            if 'name' in metadata:
                                agent_data['name'] = metadata['name']
                            elif 'title' in metadata:
                                agent_data['name'] = metadata['title']

                            if 'description' in metadata:
                                agent_data['description'] = metadata['description']

                            if 'category' in metadata:
                                agent_data['category'] = metadata['category']

                            if 'author' in metadata:
                                agent_data['author'] = metadata['author']

                            if 'version' in metadata:
                                agent_data['version'] = str(metadata['version'])

                            if 'tags' in metadata:
                                agent_data['tags'] = metadata['tags']
                    except yaml.YAMLError:
                        # Fallback to regex-based extraction for common fields if YAML fails
                        import re

                        name_match = re.search(r'^name:\s*(.*)$', front_matter, re.MULTILINE | re.IGNORECASE)
                        if not name_match:
                            name_match = re.search(r'^title:\s*(.*)$', front_matter, re.MULTILINE | re.IGNORECASE)
                        if name_match:
                            agent_data['name'] = name_match.group(1).strip().strip('"\'\'')

                        desc_match = re.search(r'^description:\s*(.*)$', front_matter, re.MULTILINE | re.IGNORECASE)
                        if desc_match:
                            agent_data['description'] = desc_match.group(1).strip().strip('"\'\'')

                        cat_match = re.search(r'^category:\s*(.*)$', front_matter, re.MULTILINE | re.IGNORECASE)
                        if cat_match:
                            agent_data['category'] = cat_match.group(1).strip().strip('"\'\'')

                        author_match = re.search(r'^author:\s*(.*)$', front_matter, re.MULTILINE | re.IGNORECASE)
                        if author_match:
                            agent_data['author'] = author_match.group(1).strip().strip('"\'\'')

            # If description is still empty, try to extract from body
            if not agent_data['description']:
                lines = content_body.strip().split('\n')
                in_description = False
                description_lines = []

                for line in lines:
                    line = line.strip()
                    if line.startswith('# ') and agent_data['name'] == filename.replace('.md', '').replace('-', ' ').title():
                         # Title line found in body
                         pass
                    elif line and not line.startswith('#') and not in_description:
                        # Start of description
                        in_description = True
                        description_lines.append(line)
                    elif line and in_description:
                        description_lines.append(line)
                    elif not line and in_description:
                        # End of paragraph
                        break

                if description_lines:
                    agent_data['description'] = ' '.join(description_lines).strip()

            return agent_data

        except Exception as e:
            logger.warning(f"Failed to parse agent markdown from {filename}: {e}")
            return None