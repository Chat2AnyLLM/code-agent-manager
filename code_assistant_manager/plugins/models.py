"""Plugin management models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Plugin:
    """Represents a plugin configuration."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None
    repo_branch: str = "main"
    plugin_path: Optional[str] = None
    local_path: Optional[str] = None
    marketplace: Optional[str] = None
    installed: bool = False
    enabled: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = int(datetime.now().timestamp() * 1000)
        if self.updated_at is None:
            self.updated_at = self.created_at

    @property
    def key(self) -> str:
        """Unique key for this plugin."""
        if self.marketplace:
            return f"{self.marketplace}:{self.name}"
        elif self.repo_owner and self.repo_name:
            return f"{self.repo_owner}/{self.repo_name}:{self.name}"
        else:
            return f"local:{self.name}"

    @property
    def github_url(self) -> Optional[str]:
        """GitHub URL for this plugin."""
        if self.repo_owner and self.repo_name:
            return f"https://github.com/{self.repo_owner}/{self.repo_name}"
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data: Dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "installed": self.installed,
            "enabled": self.enabled,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.repo_owner:
            data["repoOwner"] = self.repo_owner
        if self.repo_name:
            data["repoName"] = self.repo_name
        if self.repo_branch:
            data["repoBranch"] = self.repo_branch
        if self.plugin_path:
            data["pluginPath"] = self.plugin_path
        if self.local_path:
            data["localPath"] = self.local_path
        if self.marketplace:
            data["marketplace"] = self.marketplace
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plugin":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            repo_owner=data.get("repoOwner"),
            repo_name=data.get("repoName"),
            repo_branch=data.get("repoBranch", "main"),
            plugin_path=data.get("pluginPath"),
            local_path=data.get("localPath"),
            marketplace=data.get("marketplace"),
            installed=data.get("installed", False),
            enabled=data.get("enabled", True),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )


@dataclass
class Marketplace:
    """Represents a plugin marketplace."""

    name: str
    path: str  # Local path or GitHub URL
    description: str = ""
    enabled: bool = True
    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None

    @property
    def is_remote(self) -> bool:
        """Check if this is a remote marketplace."""
        return self.repo_owner is not None and self.repo_name is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data: Dict[str, Any] = {
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "enabled": self.enabled,
        }
        if self.repo_owner:
            data["repoOwner"] = self.repo_owner
        if self.repo_name:
            data["repoName"] = self.repo_name
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Marketplace":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            path=data["path"],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            repo_owner=data.get("repoOwner"),
            repo_name=data.get("repoName"),
        )


@dataclass
class PluginRepo:
    """Represents a pre-registered plugin repository or marketplace."""

    name: str
    description: str = ""
    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None
    repo_branch: str = "main"
    plugin_path: Optional[str] = None
    enabled: bool = True
    type: str = "plugin"  # "plugin" or "marketplace"
    aliases: List[str] = field(default_factory=list)  # Alternative names for this entry

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data: Dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "type": self.type,
        }
        if self.repo_owner:
            data["repoOwner"] = self.repo_owner
        if self.repo_name:
            data["repoName"] = self.repo_name
        if self.repo_branch:
            data["repoBranch"] = self.repo_branch
        if self.plugin_path:
            data["pluginPath"] = self.plugin_path
        if self.aliases:
            data["aliases"] = self.aliases
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginRepo":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            repo_owner=data.get("repoOwner"),
            repo_name=data.get("repoName"),
            repo_branch=data.get("repoBranch", "main"),
            plugin_path=data.get("pluginPath"),
            enabled=data.get("enabled", True),
            aliases=data.get("aliases", []),
        )
