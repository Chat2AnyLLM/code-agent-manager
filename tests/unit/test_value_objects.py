"""Unit tests for value objects."""

import pytest

from code_assistant_manager.value_objects import (
    APIKey,
    ClientName,
    EndpointName,
    EndpointURL,
    ModelID,
)


class TestEndpointURL:
    """Tests for EndpointURL value object."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        url = EndpointURL("https://api.example.com/v1")
        assert str(url) == "https://api.example.com/v1"

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        url = EndpointURL("http://localhost:8080")
        assert str(url) == "http://localhost:8080"

    def test_invalid_url_raises_error(self):
        """Test invalid URL raises ValueError."""
        with pytest.raises(ValueError):
            EndpointURL("not-a-url")

    def test_empty_url_raises_error(self):
        """Test empty URL raises ValueError."""
        with pytest.raises(ValueError):
            EndpointURL("")

    def test_immutable(self):
        """Test that value object is immutable."""
        url = EndpointURL("https://api.example.com")
        with pytest.raises(Exception):  # FrozenInstanceError
            url.value = "https://other.com"


class TestAPIKey:
    """Tests for APIKey value object."""

    def test_valid_api_key(self):
        """Test valid API key."""
        key = APIKey("sk-1234567890abcdef")
        assert key.get_value() == "sk-1234567890abcdef"

    def test_api_key_masked_in_str(self):
        """Test API key is masked in string representation."""
        key = APIKey("sk-1234567890abcdef")
        str_repr = str(key)
        # Should show partial key like "sk-1...cdef"
        assert "..." in str_repr
        assert "1234567890" not in str_repr

    def test_api_key_masked_in_repr(self):
        """Test API key is masked in repr."""
        key = APIKey("sk-1234567890abcdef")
        assert repr(key) == "APIKey(***)"

    def test_short_key_raises_error(self):
        """Test short key raises ValueError."""
        with pytest.raises(ValueError):
            APIKey("short")

    def test_empty_key_raises_error(self):
        """Test empty key raises ValueError."""
        with pytest.raises(ValueError):
            APIKey("")

    def test_immutable(self):
        """Test that value object is immutable."""
        key = APIKey("sk-1234567890abcdef")
        with pytest.raises(Exception):
            key.value = "other-key"


class TestModelID:
    """Tests for ModelID value object."""

    def test_valid_model_id(self):
        """Test valid model ID."""
        model = ModelID("gpt-4")
        assert str(model) == "gpt-4"

    def test_model_with_slash(self):
        """Test model ID with slash."""
        model = ModelID("openai/gpt-4")
        assert str(model) == "openai/gpt-4"

    def test_model_with_colon(self):
        """Test model ID with colon."""
        model = ModelID("model:version")
        assert str(model) == "model:version"

    def test_invalid_model_raises_error(self):
        """Test invalid model ID raises ValueError."""
        with pytest.raises(ValueError):
            ModelID("invalid model!")

    def test_empty_model_raises_error(self):
        """Test empty model ID raises ValueError."""
        with pytest.raises(ValueError):
            ModelID("")

    def test_equality(self):
        """Test model equality."""
        model1 = ModelID("gpt-4")
        model2 = ModelID("gpt-4")
        model3 = ModelID("gpt-3.5")

        assert model1 == model2
        assert model1 != model3

    def test_hashable(self):
        """Test model can be used in sets."""
        model1 = ModelID("gpt-4")
        model2 = ModelID("gpt-4")
        model3 = ModelID("gpt-3.5")

        models = {model1, model2, model3}
        assert len(models) == 2  # model1 and model2 are same


class TestEndpointName:
    """Tests for EndpointName value object."""

    def test_valid_name(self):
        """Test valid endpoint name."""
        name = EndpointName("litellm")
        assert str(name) == "litellm"

    def test_name_with_hyphen(self):
        """Test name with hyphen."""
        name = EndpointName("copilot-api")
        assert str(name) == "copilot-api"

    def test_name_with_underscore(self):
        """Test name with underscore."""
        name = EndpointName("my_endpoint")
        assert str(name) == "my_endpoint"

    def test_invalid_name_raises_error(self):
        """Test invalid name raises ValueError."""
        with pytest.raises(ValueError):
            EndpointName("invalid name!")

    def test_empty_name_raises_error(self):
        """Test empty name raises ValueError."""
        with pytest.raises(ValueError):
            EndpointName("")


class TestClientName:
    """Tests for ClientName value object."""

    def test_valid_client(self):
        """Test valid client name."""
        client = ClientName("claude")
        assert str(client) == "claude"

    def test_client_with_hyphen(self):
        """Test client with hyphen."""
        client = ClientName("claude-code")
        assert str(client) == "claude-code"

    def test_invalid_client_raises_error(self):
        """Test invalid client raises ValueError."""
        with pytest.raises(ValueError):
            ClientName("invalid client!")

    def test_empty_client_raises_error(self):
        """Test empty client raises ValueError."""
        with pytest.raises(ValueError):
            ClientName("")
