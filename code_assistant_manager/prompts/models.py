"""Prompt data models."""

import uuid
from datetime import datetime
from typing import Dict, Optional


def generate_prompt_id() -> str:
    """Generate a unique prompt ID."""
    return str(uuid.uuid4())[:8]


class Prompt:
    """Represents a prompt configuration."""

    def __init__(
        self,
        name: str,
        content: str,
        id: Optional[str] = None,
        description: Optional[str] = None,
        is_default: bool = False,
        created_at: Optional[int] = None,
        updated_at: Optional[int] = None,
        instruction_type: Optional[str] = None,  # "repo-wide", "path-specific", or None
        apply_to: Optional[str] = None,  # Glob pattern for path-specific instructions
        exclude_agent: Optional[str] = None,  # "coding-agent" or "code-review"
    ):
        self.id = id or generate_prompt_id()
        self.name = name
        self.content = content
        self.description = description
        self.is_default = is_default  # Only one prompt can be default
        self.created_at = created_at or int(datetime.now().timestamp() * 1000)
        self.updated_at = updated_at or int(datetime.now().timestamp() * 1000)
        self.instruction_type = instruction_type  # Type of instructions (for Copilot)
        self.apply_to = apply_to  # Glob pattern for path-specific instructions
        self.exclude_agent = exclude_agent  # Exclude certain agents

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "isDefault": self.is_default,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.description:
            data["description"] = self.description
        if self.instruction_type:
            data["instructionType"] = self.instruction_type
        if self.apply_to:
            data["applyTo"] = self.apply_to
        if self.exclude_agent:
            data["excludeAgent"] = self.exclude_agent
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Prompt":
        """Create from dictionary."""
        # Support both old 'enabled' and new 'isDefault' fields for migration
        is_default = data.get("isDefault", data.get("enabled", False))
        return cls(
            id=data["id"],
            name=data["name"],
            content=data["content"],
            description=data.get("description"),
            is_default=is_default,
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
            instruction_type=data.get("instructionType"),
            apply_to=data.get("applyTo"),
            exclude_agent=data.get("excludeAgent"),
        )
