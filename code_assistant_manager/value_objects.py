"""Value objects for Code Assistant Manager.

Immutable domain objects that wrap primitive types with validation.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EndpointURL:
    """Value object for endpoint URL with validation."""

    value: str

    def __post_init__(self):
        """Validate URL format."""
        if not self._is_valid():
            raise ValueError(f"Invalid endpoint URL: {self.value}")

    def _is_valid(self) -> bool:
        """Check if URL is valid."""
        if not self.value or len(self.value) > 2048:
            return False

        pattern = r"^https?://(localhost|127\.0\.0\.1|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})(:[0-9]+)?(/.*)?$"
        return bool(re.match(pattern, self.value))

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"EndpointURL('{self.value}')"


@dataclass(frozen=True)
class APIKey:
    """Value object for API key with validation and secure representation."""

    value: str

    def __post_init__(self):
        """Validate API key format."""
        if not self._is_valid():
            raise ValueError("Invalid API key format")

    def _is_valid(self) -> bool:
        """Check if API key is valid."""
        if not self.value or len(self.value) < 10:
            return False

        # Allow alphanumeric, dots, hyphens, underscores, equals
        return not bool(re.search(r"[^a-zA-Z0-9._=-]", self.value))

    def __str__(self) -> str:
        """Return masked representation for security."""
        if len(self.value) <= 8:
            return "***"
        return f"{self.value[:4]}...{self.value[-4:]}"

    def __repr__(self) -> str:
        """Return masked representation for security."""
        return "APIKey(***)"

    def get_value(self) -> str:
        """Get the actual API key value (use with caution)."""
        return self.value


@dataclass(frozen=True)
class ModelID:
    """Value object for model identifier with validation."""

    value: str

    def __post_init__(self):
        """Validate model ID format."""
        if not self._is_valid():
            raise ValueError(f"Invalid model ID: {self.value}")

    def _is_valid(self) -> bool:
        """Check if model ID is valid."""
        if not self.value:
            return False
        return bool(re.match(r"^[a-zA-Z0-9._:/\-]+$", self.value))

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ModelID('{self.value}')"

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other) -> bool:
        if isinstance(other, ModelID):
            return self.value == other.value
        return False


@dataclass(frozen=True)
class EndpointName:
    """Value object for endpoint name with validation."""

    value: str

    def __post_init__(self):
        """Validate endpoint name format."""
        if not self._is_valid():
            raise ValueError(f"Invalid endpoint name: {self.value}")

    def _is_valid(self) -> bool:
        """Check if endpoint name is valid."""
        if not self.value or len(self.value) > 100:
            return False
        # Allow alphanumeric, hyphens, underscores
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", self.value))

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"EndpointName('{self.value}')"

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class ClientName:
    """Value object for client name with validation."""

    value: str

    def __post_init__(self):
        """Validate client name format."""
        if not self._is_valid():
            raise ValueError(f"Invalid client name: {self.value}")

    def _is_valid(self) -> bool:
        """Check if client name is valid."""
        if not self.value or len(self.value) > 50:
            return False
        # Allow alphanumeric, hyphens, underscores
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", self.value))

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ClientName('{self.value}')"
