"""Tests for CLI options module to ensure all options are properly defined."""

import pytest
from typer.models import OptionInfo

from code_assistant_manager.cli.options import (
    CONFIG_FILE_OPTION,
    CONFIG_OPTION,
    DEBUG_OPTION,
    ENDPOINTS_OPTION,
    FORCE_OPTION,
    INSTALL_ALIAS_TARGET_OPTION,
    KEEP_CONFIG_OPTION,
    SCOPE_OPTION,
    TARGET_OPTION,
    TOOL_ARGS_OPTION,
    TOOL_NAME_OPTION,
    UNINSTALL_TARGET_OPTION,
    UPGRADE_ALIAS_TARGET_OPTION,
    VALIDATE_VERBOSE_OPTION,
    VERBOSE_DOCTOR_OPTION,
    VERBOSE_OPTION,
    VERSION_OPTION,
)


class TestCLIOptions:
    """Test all CLI option definitions."""

    def test_config_file_option(self):
        """Test CONFIG_FILE_OPTION is properly defined."""
        assert isinstance(CONFIG_FILE_OPTION, OptionInfo)
        assert CONFIG_FILE_OPTION.default is None
        assert "--config" in CONFIG_FILE_OPTION.param_decls
        assert "-c" in CONFIG_FILE_OPTION.param_decls

    def test_config_option(self):
        """Test CONFIG_OPTION is properly defined."""
        assert isinstance(CONFIG_OPTION, OptionInfo)
        assert CONFIG_OPTION.default is None
        assert "--config" in CONFIG_OPTION.param_decls
        assert "-c" in CONFIG_OPTION.param_decls
        assert "settings.conf" in CONFIG_OPTION.help

    def test_debug_option(self):
        """Test DEBUG_OPTION is properly defined."""
        assert isinstance(DEBUG_OPTION, OptionInfo)
        assert DEBUG_OPTION.default is False
        assert "--debug" in DEBUG_OPTION.param_decls
        assert "-d" in DEBUG_OPTION.param_decls

    def test_endpoints_option(self):
        """Test ENDPOINTS_OPTION is properly defined."""
        assert isinstance(ENDPOINTS_OPTION, OptionInfo)
        assert ENDPOINTS_OPTION.default is None
        assert "--endpoints" in ENDPOINTS_OPTION.param_decls

    def test_force_option(self):
        """Test FORCE_OPTION is properly defined."""
        assert isinstance(FORCE_OPTION, OptionInfo)
        assert FORCE_OPTION.default is False
        assert "--force" in FORCE_OPTION.param_decls
        assert "-f" in FORCE_OPTION.param_decls

    def test_install_alias_target_option(self):
        """Test INSTALL_ALIAS_TARGET_OPTION is properly defined."""
        from typer.models import ArgumentInfo
        assert isinstance(INSTALL_ALIAS_TARGET_OPTION, ArgumentInfo)
        assert INSTALL_ALIAS_TARGET_OPTION.default == "all"

    def test_keep_config_option(self):
        """Test KEEP_CONFIG_OPTION is properly defined."""
        assert isinstance(KEEP_CONFIG_OPTION, OptionInfo)
        assert KEEP_CONFIG_OPTION.default is False
        assert "--keep-config" in KEEP_CONFIG_OPTION.param_decls
        assert "-k" in KEEP_CONFIG_OPTION.param_decls

    def test_scope_option(self):
        """Test SCOPE_OPTION is properly defined."""
        assert isinstance(SCOPE_OPTION, OptionInfo)
        assert SCOPE_OPTION.default == "user"
        assert "--scope" in SCOPE_OPTION.param_decls
        assert "-s" in SCOPE_OPTION.param_decls

    def test_target_option(self):
        """Test TARGET_OPTION is properly defined."""
        from typer.models import ArgumentInfo
        assert isinstance(TARGET_OPTION, ArgumentInfo)
        assert TARGET_OPTION.default == "all"

    def test_tool_args_option(self):
        """Test TOOL_ARGS_OPTION is properly defined."""
        from typer.models import ArgumentInfo
        assert isinstance(TOOL_ARGS_OPTION, ArgumentInfo)
        assert TOOL_ARGS_OPTION.default is None

    def test_tool_name_option(self):
        """Test TOOL_NAME_OPTION is properly defined."""
        from typer.models import ArgumentInfo
        assert isinstance(TOOL_NAME_OPTION, ArgumentInfo)
        assert TOOL_NAME_OPTION.default is None

    def test_uninstall_target_option(self):
        """Test UNINSTALL_TARGET_OPTION is properly defined."""
        from typer.models import ArgumentInfo
        assert isinstance(UNINSTALL_TARGET_OPTION, ArgumentInfo)
        assert UNINSTALL_TARGET_OPTION.default == ...

    def test_upgrade_alias_target_option(self):
        """Test UPGRADE_ALIAS_TARGET_OPTION is properly defined."""
        from typer.models import ArgumentInfo
        assert isinstance(UPGRADE_ALIAS_TARGET_OPTION, ArgumentInfo)
        assert UPGRADE_ALIAS_TARGET_OPTION.default == "all"

    def test_validate_verbose_option(self):
        """Test VALIDATE_VERBOSE_OPTION is properly defined."""
        assert isinstance(VALIDATE_VERBOSE_OPTION, OptionInfo)
        assert VALIDATE_VERBOSE_OPTION.default is False
        assert "--verbose" in VALIDATE_VERBOSE_OPTION.param_decls
        assert "-v" in VALIDATE_VERBOSE_OPTION.param_decls

    def test_verbose_doctor_option(self):
        """Test VERBOSE_DOCTOR_OPTION is properly defined."""
        assert isinstance(VERBOSE_DOCTOR_OPTION, OptionInfo)
        assert VERBOSE_DOCTOR_OPTION.default is False
        assert "--verbose" in VERBOSE_DOCTOR_OPTION.param_decls
        assert "-v" in VERBOSE_DOCTOR_OPTION.param_decls

    def test_verbose_option(self):
        """Test VERBOSE_OPTION is properly defined."""
        assert isinstance(VERBOSE_OPTION, OptionInfo)
        assert VERBOSE_OPTION.default is False
        assert "--verbose" in VERBOSE_OPTION.param_decls
        assert "-v" in VERBOSE_OPTION.param_decls

    def test_version_option(self):
        """Test VERSION_OPTION is properly defined."""
        assert isinstance(VERSION_OPTION, OptionInfo)
        assert VERSION_OPTION.default is None
        assert "--version" in VERSION_OPTION.param_decls

    def test_all_options_have_help_text(self):
        """Test that all options have help text."""
        options = [
            CONFIG_FILE_OPTION,
            CONFIG_OPTION,
            DEBUG_OPTION,
            ENDPOINTS_OPTION,
            FORCE_OPTION,
            KEEP_CONFIG_OPTION,
            SCOPE_OPTION,
            VALIDATE_VERBOSE_OPTION,
            VERBOSE_DOCTOR_OPTION,
            VERBOSE_OPTION,
            VERSION_OPTION,
        ]

        for option in options:
            assert option.help is not None
            assert len(option.help.strip()) > 0

    def test_arguments_have_help_text(self):
        """Test that all arguments have help text."""
        arguments = [
            INSTALL_ALIAS_TARGET_OPTION,
            TARGET_OPTION,
            TOOL_ARGS_OPTION,
            TOOL_NAME_OPTION,
            UNINSTALL_TARGET_OPTION,
            UPGRADE_ALIAS_TARGET_OPTION,
        ]

        for arg in arguments:
            assert arg.help is not None
            assert len(arg.help.strip()) > 0