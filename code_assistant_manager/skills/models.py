"""Skill models for Code Assistant Manager."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Skill:
    """Represents a skill configuration."""

    key: str
    name: str
    description: str
    directory: str  # The skill folder name for installation
    installed: bool = False
    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None
    repo_branch: Optional[str] = "main"
    skills_path: Optional[str] = None
    readme_url: Optional[str] = None
    source_directory: Optional[str] = None  # Full path in repo relative to skills_path

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "directory": self.directory,
            "installed": self.installed,
        }
        if self.repo_owner:
            data["repoOwner"] = self.repo_owner
        if self.repo_name:
            data["repoName"] = self.repo_name
        if self.repo_branch:
            data["repoBranch"] = self.repo_branch
        if self.skills_path:
            data["skillsPath"] = self.skills_path
        if self.readme_url:
            data["readmeUrl"] = self.readme_url
        if self.source_directory:
            data["sourceDirectory"] = self.source_directory
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Skill":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            name=data["name"],
            description=data["description"],
            directory=data["directory"],
            installed=data.get("installed", False),
            repo_owner=data.get("repoOwner"),
            repo_name=data.get("repoName"),
            repo_branch=data.get("repoBranch", "main"),
            skills_path=data.get("skillsPath"),
            readme_url=data.get("readmeUrl"),
            source_directory=data.get("sourceDirectory"),
        )


@dataclass
class SkillRepo:
    """Represents a skill repository."""

    owner: str
    name: str
    branch: str = "main"
    enabled: bool = True
    skills_path: Optional[str] = None
    exclude: Optional[List[str]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = {
            "owner": self.owner,
            "name": self.name,
            "branch": self.branch,
            "enabled": self.enabled,
        }
        if self.skills_path:
            data["skillsPath"] = self.skills_path
        if self.exclude:
            data["exclude"] = self.exclude
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "SkillRepo":
        """Create from dictionary."""
        return cls(
            owner=data["owner"],
            name=data["name"],
            branch=data.get("branch", "main"),
            enabled=data.get("enabled", True),
            skills_path=data.get("skillsPath"),
            exclude=data.get("exclude"),
        )
