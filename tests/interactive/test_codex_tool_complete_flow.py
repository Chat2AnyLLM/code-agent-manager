"""Test for codex tool with complete menu flow using key providers."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.tools.codex import CodexTool


class TestCodexToolCompleteFlow:
    """Test suite for codex tool with complete menu flow."""

    def setup_method(self):
        """Set up test environment."""
        # Create a temporary config file for testing
        self.temp_config = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        config_data = {
            "common": {"cache_ttl_seconds": 3600},
            "endpoints": {
                "test_endpoint": {
                    "endpoint": "https://api.test.com",
                    "api_key": "test_key",
                    "description": "Test Endpoint",
                    "list_models_cmd": "echo model1 model2 model3",
                    "supported_client": "codex",
                }
            },
        }
        json.dump(config_data, self.temp_config, indent=2)
        self.temp_config.close()

        # Create config manager
        self.config = ConfigManager(self.temp_config.name)

    def teardown_method(self):
        """Clean up test environment."""
        # Remove temporary config file
        if hasattr(self, "temp_config") and self.temp_config:
            os.unlink(self.temp_config.name)

    def test_codex_tool_complete_flow_with_key_providers(self):
        """Test codex tool with complete flow using key providers to avoid deadloops."""
        # Mock the command availability check
        with patch(
            "code_assistant_manager.tools.base.CLITool._check_command_available"
        ) as mock_check_command:
            mock_check_command.return_value = True

            # Mock subprocess.run to avoid actually running codex
            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0)

                # Mock the endpoint manager methods
                with patch(
                    "code_assistant_manager.tools.EndpointManager"
                ) as mock_endpoint_manager:
                    mock_em_instance = MagicMock()
                    mock_endpoint_manager.return_value = mock_em_instance

                    # Mock endpoint selection - select first endpoint
                    mock_em_instance.select_endpoint.return_value = (
                        True,
                        "test_endpoint",
                    )

                    # Mock endpoint config retrieval
                    mock_em_instance.get_endpoint_config.return_value = (
                        True,
                        {
                            "endpoint": "https://api.test.com",
                            "actual_api_key": "test_key",
                        },
                    )

                    # Mock model fetching
                    mock_em_instance.fetch_models.return_value = (
                        True,
                        ["model1", "model2", "model3"],
                    )

                    # Mock the upgrade/installation prompts to skip them
                    with patch(
                        "code_assistant_manager.tools.base.CLITool._prompt_for_upgrade"
                    ) as mock_upgrade:
                        mock_upgrade.return_value = False  # Skip upgrade

                        with patch(
                            "code_assistant_manager.tools.base.CLITool._prompt_for_installation"
                        ) as mock_install:
                            mock_install.return_value = (
                                False  # Skip installation (tool already installed)
                            )

                        # Mock menus (model selection)
                        with patch(
                            "code_assistant_manager.menu.menus.display_centered_menu",
                            return_value=(True, 0),
                        ):
                            # Create and run the tool
                            tool = CodexTool(self.config)
                            result = tool.run([])

                            # Verify the tool ran successfully
                            assert result == 0

                            # Verify that the expected methods were called
                            mock_em_instance.get_endpoint_config.assert_called_once_with(
                                "test_endpoint"
                            )
                            mock_em_instance.fetch_models.assert_called_once()

                            # Verify that subprocess.run was called with the expected arguments
                            mock_subprocess.assert_called_once()

    def test_codex_tool_with_upgrade_prompt_key_provider(self):
        """Test codex tool with upgrade prompt using key provider."""
        # Mock the command availability check
        with patch(
            "code_assistant_manager.tools.base.CLITool._check_command_available"
        ) as mock_check_command:
            mock_check_command.return_value = True

            # Mock subprocess.run to avoid actually running codex
            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0)

                # Mock the endpoint manager methods
                with patch(
                    "code_assistant_manager.tools.EndpointManager"
                ) as mock_endpoint_manager:
                    mock_em_instance = MagicMock()
                    mock_endpoint_manager.return_value = mock_em_instance

                    # Mock endpoint selection - select first endpoint
                    mock_em_instance.select_endpoint.return_value = (
                        True,
                        "test_endpoint",
                    )

                    # Mock endpoint config retrieval
                    mock_em_instance.get_endpoint_config.return_value = (
                        True,
                        {
                            "endpoint": "https://api.test.com",
                            "actual_api_key": "test_key",
                        },
                    )

                    # Mock model fetching
                    mock_em_instance.fetch_models.return_value = (
                        True,
                        ["model1", "model2", "model3"],
                    )

                    # Mock the upgrade/installation prompts to simulate user choices
                    with patch(
                        "code_assistant_manager.tools.base.CLITool._prompt_for_upgrade"
                    ) as mock_upgrade:
                        mock_upgrade.return_value = True  # User chooses to upgrade

                        with patch(
                            "code_assistant_manager.tools.base.CLITool._perform_upgrade"
                        ) as mock_perform_upgrade:
                            mock_perform_upgrade.return_value = True  # Upgrade succeeds

                            with patch(
                                "code_assistant_manager.tools.base.CLITool._prompt_for_installation"
                            ) as mock_install:
                                mock_install.return_value = (
                                    False  # Skip installation (tool already installed)
                                )

                            # Mock menus (model selection)
                            with patch(
                                "code_assistant_manager.menu.menus.display_centered_menu",
                                return_value=(True, 0),
                            ):

                                # Create and run the tool
                                tool = CodexTool(self.config)
                                result = tool.run([])

                                # Verify the tool ran successfully
                                assert result == 0

                                # Verify that upgrade was attempted
                                mock_upgrade.assert_called_once()
                                mock_perform_upgrade.assert_called_once()

    def test_codex_tool_with_installation_prompt_key_provider(self):
        """Test codex tool with installation prompt using key provider."""
        # Mock the command availability check - tool not installed
        with patch(
            "code_assistant_manager.tools.base.CLITool._check_command_available"
        ) as mock_check_command:
            mock_check_command.return_value = False  # Tool not installed

            # Mock subprocess.run to avoid actually running installation commands
            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0)

                # Mock the tool registry to return an install command
                with patch(
                    "code_assistant_manager.tools.registry.TOOL_REGISTRY.get_install_command"
                ) as mock_get_install_cmd:
                    mock_get_install_cmd.return_value = "echo 'Installing codex'"

                    # Mock command check after installation
                    with patch(
                        "code_assistant_manager.tools.base.CLITool._check_command_available"
                    ) as mock_check_after_install:
                        # First call returns False (not installed), second returns True (installed)
                        mock_check_after_install.side_effect = [False, True]

                        # Mock the endpoint manager methods
                        with patch(
                            "code_assistant_manager.tools.EndpointManager"
                        ) as mock_endpoint_manager:
                            mock_em_instance = MagicMock()
                            mock_endpoint_manager.return_value = mock_em_instance

                            # Codex now iterates endpoints one-by-one (no select_endpoint call)

                            # Mock endpoint config retrieval
                            mock_em_instance.get_endpoint_config.return_value = (
                                True,
                                {
                                    "endpoint": "https://api.test.com",
                                    "actual_api_key": "test_key",
                                },
                            )

                            # Mock model fetching
                            mock_em_instance.fetch_models.return_value = (
                                True,
                                ["model1", "model2", "model3"],
                            )

                            # Mock the installation prompts to simulate user choices
                            with patch(
                                "code_assistant_manager.tools.base.CLITool._prompt_for_installation"
                            ) as mock_install:
                                mock_install.return_value = (
                                    True  # User chooses to install
                                )

                                with patch(
                                    "code_assistant_manager.tools.base.CLITool._perform_installation"
                                ) as mock_perform_install:
                                    mock_perform_install.return_value = (
                                        True  # Installation succeeds
                                    )

                                    # Mock menus (model selection)
                                    with patch(
                                        "code_assistant_manager.menu.menus.display_centered_menu",
                                        return_value=(True, 0),
                                    ):
                                        # Create and run the tool
                                        tool = CodexTool(self.config)
                                        result = tool.run([])

                                        # Verify the tool ran successfully
                                        assert result == 0

                                        # Verify that installation was attempted
                                        mock_install.assert_called_once()
                                        mock_perform_install.assert_called_once()

    def test_codex_tool_skip_upgrade_no_deadloop(self):
        """Test that selecting 'Skip' on upgrade menu doesn't cause deadloop."""
        # Mock the command availability check - tool is installed
        with patch(
            "code_assistant_manager.tools.base.CLITool._check_command_available"
        ) as mock_check_command:
            mock_check_command.return_value = True  # Tool is installed

            # Mock subprocess.run to avoid actually running codex
            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0)

                # Mock the endpoint manager methods
                with patch(
                    "code_assistant_manager.tools.EndpointManager"
                ) as mock_endpoint_manager:
                    mock_em_instance = MagicMock()
                    mock_endpoint_manager.return_value = mock_em_instance

                    # Mock endpoint selection - select first endpoint
                    mock_em_instance.select_endpoint.return_value = (
                        True,
                        "test_endpoint",
                    )

                    # Mock endpoint config retrieval
                    mock_em_instance.get_endpoint_config.return_value = (
                        True,
                        {
                            "endpoint": "https://api.test.com",
                            "actual_api_key": "test_key",
                        },
                    )

                    # Mock model fetching
                    mock_em_instance.fetch_models.return_value = (
                        True,
                        ["model1", "model2", "model3"],
                    )

                    # Mock the upgrade prompt to simulate user selecting 'Skip'
                    with patch(
                        "code_assistant_manager.tools.base.CLITool._prompt_for_upgrade"
                    ) as mock_upgrade:
                        mock_upgrade.return_value = (
                            False  # User chooses to skip upgrade
                        )

                        # Mock menus (model selection)
                        with patch(
                            "code_assistant_manager.menu.menus.display_centered_menu",
                            return_value=(True, 0),
                        ):
                            # Create and run the tool
                            tool = CodexTool(self.config)
                            result = tool.run([])

                            # Verify the tool ran successfully
                            assert result == 0

                            # Verify that upgrade was offered but skipped
                            mock_upgrade.assert_called_once()

                            # Verify that the tool continued normally after skipping upgrade
                            mock_em_instance.get_endpoint_config.assert_called_once_with(
                                "test_endpoint"
                            )
                            mock_em_instance.fetch_models.assert_called_once()
                            mock_subprocess.assert_called_once()


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
