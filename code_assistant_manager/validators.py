"""Chain of Responsibility pattern for validation.

Provides flexible validation pipelines.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from .value_objects import APIKey, EndpointURL, ModelID


class ValidationHandler(ABC):
    """Base validator in chain of responsibility."""

    def __init__(self, next_handler: Optional["ValidationHandler"] = None):
        """
        Initialize validator.

        Args:
            next_handler: Next validator in the chain
        """
        self._next = next_handler

    def validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate data and pass to next handler.

        Args:
            data: Data to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        is_valid, errors = self._do_validate(data)

        if not is_valid:
            return False, errors

        if self._next:
            return self._next.validate(data)

        return True, []

    @abstractmethod
    def _do_validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Perform actual validation.

        Args:
            data: Data to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """

    def set_next(self, handler: "ValidationHandler") -> "ValidationHandler":
        """
        Set next handler in chain.

        Args:
            handler: Next handler

        Returns:
            The handler that was set (for chaining)
        """
        self._next = handler
        return handler


class URLValidator(ValidationHandler):
    """Validates endpoint URLs."""

    def _do_validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate URL field."""
        url = data.get("endpoint", "")
        if not url:
            return False, ["Missing endpoint URL"]

        try:
            EndpointURL(url)
            return True, []
        except ValueError as e:
            return False, [str(e)]


class APIKeyValidator(ValidationHandler):
    """Validates API keys."""

    def _do_validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate API key field if present."""
        api_key = data.get("api_key", "")

        # API key is optional
        if not api_key:
            return True, []

        try:
            APIKey(api_key)
            return True, []
        except ValueError as e:
            return False, [str(e)]


class ModelIDValidator(ValidationHandler):
    """Validates model IDs."""

    def _do_validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate model ID if present."""
        model_id = data.get("model_id", "")

        # Model ID is optional
        if not model_id:
            return True, []

        try:
            ModelID(model_id)
            return True, []
        except ValueError as e:
            return False, [str(e)]


class ProxyValidator(ValidationHandler):
    """Validates proxy configuration."""

    def _do_validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate proxy settings if present."""
        errors = []

        # Validate HTTP proxy
        http_proxy = data.get("http_proxy", "")
        if http_proxy and not self._is_valid_proxy_url(http_proxy):
            errors.append(f"Invalid HTTP proxy URL: {http_proxy}")

        # Validate HTTPS proxy
        https_proxy = data.get("https_proxy", "")
        if https_proxy and not self._is_valid_proxy_url(https_proxy):
            errors.append(f"Invalid HTTPS proxy URL: {https_proxy}")

        return len(errors) == 0, errors

    def _is_valid_proxy_url(self, url: str) -> bool:
        """Check if proxy URL is valid."""
        try:
            EndpointURL(url)
            return True
        except ValueError:
            return False


class BooleanValidator(ValidationHandler):
    """Validates boolean fields."""

    def __init__(
        self, field_names: List[str], next_handler: Optional["ValidationHandler"] = None
    ):
        """
        Initialize boolean validator.

        Args:
            field_names: Names of fields to validate as booleans
            next_handler: Next validator in chain
        """
        super().__init__(next_handler)
        self.field_names = field_names

    def _do_validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate boolean fields."""
        errors = []

        for field_name in self.field_names:
            value = data.get(field_name)
            if value is None:
                continue

            if not self._is_valid_boolean(value):
                errors.append(f"Invalid boolean value for {field_name}: {value}")

        return len(errors) == 0, errors

    def _is_valid_boolean(self, value) -> bool:
        """Check if value is a valid boolean representation."""
        if isinstance(value, bool):
            return True

        if isinstance(value, str):
            return value.lower() in ("true", "false", "1", "0", "yes", "no")

        return False


class RequiredFieldsValidator(ValidationHandler):
    """Validates that required fields are present."""

    def __init__(
        self,
        required_fields: List[str],
        next_handler: Optional["ValidationHandler"] = None,
    ):
        """
        Initialize required fields validator.

        Args:
            required_fields: List of required field names
            next_handler: Next validator in chain
        """
        super().__init__(next_handler)
        self.required_fields = required_fields

    def _do_validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate required fields are present."""
        errors = []

        for field in self.required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")

        return len(errors) == 0, errors


class CommandValidator(ValidationHandler):
    """Validates command strings and model lists."""

    def _do_validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate command string and list of models if present."""
        errors = []
        
        # Validate list_models_cmd if present
        command = data.get("list_models_cmd", "")
        if command and not self._is_safe_command(command):
            errors.append("Command contains potentially dangerous patterns")
        
        # Validate list_of_models if present
        list_of_models = data.get("list_of_models", None)
        if list_of_models is not None:
            if not isinstance(list_of_models, list):
                errors.append("list_of_models must be a list")
            else:
                from .config import validate_model_id
                for model in list_of_models:
                    if not validate_model_id(str(model)):
                        errors.append(f"Invalid model ID in list_of_models: {model}")
        
        if errors:
            return False, errors
        return True, []

    def _is_safe_command(self, command: str) -> bool:
        """Check if command is safe (basic check)."""
        # Import validation function from config module
        from .config import validate_command

        return validate_command(command)


class ValidationPipeline:
    """Builder for creating validation pipelines."""

    def __init__(self):
        """Initialize empty pipeline."""
        self._first_handler: Optional[ValidationHandler] = None
        self._last_handler: Optional[ValidationHandler] = None

    def add(self, handler: ValidationHandler) -> "ValidationPipeline":
        """
        Add a validator to the pipeline.

        Args:
            handler: Validator to add

        Returns:
            Self for chaining
        """
        if self._first_handler is None:
            self._first_handler = handler
            self._last_handler = handler
        else:
            self._last_handler.set_next(handler)
            self._last_handler = handler

        return self

    def validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Run validation pipeline.

        Args:
            data: Data to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if self._first_handler is None:
            return True, []

        return self._first_handler.validate(data)

    @classmethod
    def for_endpoint_config(cls) -> "ValidationPipeline":
        """Create a standard validation pipeline for endpoint configuration."""
        return (
            cls()
            .add(RequiredFieldsValidator(["endpoint"]))
            .add(URLValidator())
            .add(APIKeyValidator())
            .add(ProxyValidator())
            .add(BooleanValidator(["use_proxy", "keep_proxy_config"]))
            .add(CommandValidator())
        )

    @classmethod
    def for_common_config(cls) -> "ValidationPipeline":
        """Create a validation pipeline for common configuration."""
        return cls().add(ProxyValidator())


class ConfigValidator:
    """High-level validator for complete configuration."""

    def __init__(self):
        """Initialize validator with pipelines."""
        self.endpoint_pipeline = ValidationPipeline.for_endpoint_config()
        self.common_pipeline = ValidationPipeline.for_common_config()

    def validate_endpoint(self, endpoint_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate endpoint configuration.

        Args:
            endpoint_data: Endpoint configuration data

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return self.endpoint_pipeline.validate(endpoint_data)

    def validate_common(self, common_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate common configuration.

        Args:
            common_data: Common configuration data

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return self.common_pipeline.validate(common_data)

    def validate_all_endpoints(
        self, endpoints: Dict[str, Dict]
    ) -> Tuple[bool, List[str]]:
        """
        Validate all endpoints in configuration.

        Args:
            endpoints: Dictionary of endpoint configurations

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        all_errors = []

        for endpoint_name, endpoint_data in endpoints.items():
            is_valid, errors = self.validate_endpoint(endpoint_data)
            if not is_valid:
                prefixed_errors = [f"[{endpoint_name}] {error}" for error in errors]
                all_errors.extend(prefixed_errors)

        return len(all_errors) == 0, all_errors
