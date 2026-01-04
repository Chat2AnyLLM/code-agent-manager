"""Agent models for Code Assistant Manager."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Agent:
    """Represents an agent configuration."""

    key: str
    name: str
    description: str
    filename: str  # The .md filename
    installed: bool = False
    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None
    repo_branch: Optional[str] = "main"
    agents_path: Optional[str] = None
    readme_url: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    color: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "filename": self.filename,
            "installed": self.installed,
        }
        if self.repo_owner:
            data["repoOwner"] = self.repo_owner
        if self.repo_name:
            data["repoName"] = self.repo_name
        if self.repo_branch:
            data["repoBranch"] = self.repo_branch
        if self.agents_path:
            data["agentsPath"] = self.agents_path
        if self.readme_url:
            data["readmeUrl"] = self.readme_url
        if self.tools:
            data["tools"] = self.tools
        if self.color:
            data["color"] = self.color
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Agent":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            name=data["name"],
            description=data["description"],
            filename=data["filename"],
            installed=data.get("installed", False),
            repo_owner=data.get("repoOwner"),
            repo_name=data.get("repoName"),
            repo_branch=data.get("repoBranch", "main"),
            agents_path=data.get("agentsPath"),
            readme_url=data.get("readmeUrl"),
            tools=data.get("tools", []),
            color=data.get("color"),
        )


@dataclass
class AgentRepo:
    """Represents an agent repository."""

    owner: str
    name: str
    branch: str = "main"
    enabled: bool = True
    agents_path: Optional[str] = None
    exclude: Optional[List[str]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = {
            "owner": self.owner,
            "name": self.name,
            "branch": self.branch,
            "enabled": self.enabled,
        }
        if self.agents_path:
            data["agentsPath"] = self.agents_path
        if self.exclude:
            data["exclude"] = self.exclude
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentRepo":
        """Create from dictionary."""
        return cls(
            owner=data["owner"],
            name=data["name"],
            branch=data.get("branch", "main"),
            enabled=data.get("enabled", True),
            agents_path=data.get("agentsPath"),
            exclude=data.get("exclude"),
        )
