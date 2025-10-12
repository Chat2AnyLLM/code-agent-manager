"""Unit tests for validation chain of responsibility."""

import pytest

from code_assistant_manager.validators import (
    APIKeyValidator,
    BooleanValidator,
    ConfigValidator,
    ModelIDValidator,
    ProxyValidator,
    RequiredFieldsValidator,
    URLValidator,
    ValidationPipeline,
)


class TestURLValidator:
    """Tests for URLValidator."""

    def test_valid_url(self):
        """Test valid URL passes validation."""
        validator = URLValidator()
        is_valid, errors = validator.validate({"endpoint": "https://api.example.com"})

        assert is_valid
        assert len(errors) == 0

    def test_invalid_url(self):
        """Test invalid URL fails validation."""
        validator = URLValidator()
        is_valid, errors = validator.validate({"endpoint": "not-a-url"})

        assert not is_valid
        assert len(errors) > 0

    def test_missing_url(self):
        """Test missing URL fails validation."""
        validator = URLValidator()
        is_valid, errors = validator.validate({})

        assert not is_valid
        assert len(errors) > 0


class TestAPIKeyValidator:
    """Tests for APIKeyValidator."""

    def test_valid_api_key(self):
        """Test valid API key passes validation."""
        validator = APIKeyValidator()
        is_valid, errors = validator.validate({"api_key": "sk-1234567890abcdef"})

        assert is_valid
        assert len(errors) == 0

    def test_missing_api_key(self):
        """Test missing API key passes (optional)."""
        validator = APIKeyValidator()
        is_valid, errors = validator.validate({})

        assert is_valid
        assert len(errors) == 0

    def test_invalid_api_key(self):
        """Test invalid API key fails validation."""
        validator = APIKeyValidator()
        is_valid, errors = validator.validate({"api_key": "short"})

        assert not is_valid
        assert len(errors) > 0


class TestRequiredFieldsValidator:
    """Tests for RequiredFieldsValidator."""

    def test_all_required_fields_present(self):
        """Test all required fields present passes."""
        validator = RequiredFieldsValidator(["field1", "field2"])
        is_valid, errors = validator.validate({"field1": "value1", "field2": "value2"})

        assert is_valid
        assert len(errors) == 0

    def test_missing_required_field(self):
        """Test missing required field fails."""
        validator = RequiredFieldsValidator(["field1", "field2"])
        is_valid, errors = validator.validate({"field1": "value1"})

        assert not is_valid
        assert len(errors) > 0
        assert "field2" in errors[0]


class TestBooleanValidator:
    """Tests for BooleanValidator."""

    def test_valid_boolean_true(self):
        """Test valid boolean true."""
        validator = BooleanValidator(["flag"])
        is_valid, errors = validator.validate({"flag": True})

        assert is_valid

    def test_valid_boolean_string(self):
        """Test valid boolean string."""
        validator = BooleanValidator(["flag"])
        is_valid, errors = validator.validate({"flag": "true"})

        assert is_valid

    def test_invalid_boolean(self):
        """Test invalid boolean value."""
        validator = BooleanValidator(["flag"])
        is_valid, errors = validator.validate({"flag": "maybe"})

        assert not is_valid
        assert len(errors) > 0


class TestValidationPipeline:
    """Tests for ValidationPipeline."""

    def test_pipeline_with_single_validator(self):
        """Test pipeline with single validator."""
        pipeline = ValidationPipeline().add(URLValidator())

        is_valid, errors = pipeline.validate({"endpoint": "https://api.example.com"})
        assert is_valid

    def test_pipeline_with_multiple_validators(self):
        """Test pipeline with multiple validators."""
        pipeline = ValidationPipeline().add(URLValidator()).add(APIKeyValidator())

        is_valid, errors = pipeline.validate(
            {"endpoint": "https://api.example.com", "api_key": "sk-1234567890abcdef"}
        )
        assert is_valid

    def test_pipeline_stops_on_first_error(self):
        """Test pipeline stops on first validation error."""
        pipeline = ValidationPipeline().add(URLValidator()).add(APIKeyValidator())

        is_valid, errors = pipeline.validate(
            {"endpoint": "invalid-url", "api_key": "sk-1234567890abcdef"}
        )

        assert not is_valid
        assert len(errors) > 0

    def test_for_endpoint_config(self):
        """Test standard endpoint config pipeline."""
        pipeline = ValidationPipeline.for_endpoint_config()

        is_valid, errors = pipeline.validate(
            {
                "endpoint": "https://api.example.com",
                "api_key": "sk-1234567890abcdef",
                "use_proxy": "false",
            }
        )

        assert is_valid


class TestConfigValidator:
    """Tests for ConfigValidator."""

    def test_validate_endpoint(self):
        """Test endpoint validation."""
        validator = ConfigValidator()

        is_valid, errors = validator.validate_endpoint(
            {"endpoint": "https://api.example.com", "api_key": "sk-1234567890abcdef"}
        )

        assert is_valid

    def test_validate_all_endpoints(self):
        """Test validating multiple endpoints."""
        validator = ConfigValidator()

        endpoints = {
            "endpoint1": {
                "endpoint": "https://api1.example.com",
                "api_key": "sk-1234567890abcdef",
            },
            "endpoint2": {
                "endpoint": "https://api2.example.com",
                "api_key": "sk-0987654321fedcba",
            },
        }

        is_valid, errors = validator.validate_all_endpoints(endpoints)
        assert is_valid

    def test_validate_all_endpoints_with_error(self):
        """Test validating multiple endpoints with error."""
        validator = ConfigValidator()

        endpoints = {
            "good_endpoint": {
                "endpoint": "https://api.example.com",
                "api_key": "sk-1234567890abcdef",
            },
            "bad_endpoint": {
                "endpoint": "invalid-url",
                "api_key": "sk-0987654321fedcba",
            },
        }

        is_valid, errors = validator.validate_all_endpoints(endpoints)
        assert not is_valid
        assert "bad_endpoint" in errors[0]
