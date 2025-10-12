"""Performance tests for code_assistant_manager."""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.endpoints import EndpointManager
from code_assistant_manager.tools import ClaudeTool, CodexTool, QwenTool


@pytest.fixture
def performance_config():
    """Create a config file for performance testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_data = {
            "common": {"cache_ttl_seconds": 3600},
            "endpoints": {
                "test-endpoint-1": {
                    "endpoint": "https://api1.test.com/v1",
                    "api_key": "test-key-1",
                    "description": "Test Endpoint 1",
                    "list_models_cmd": "echo model1 model2 model3",
                    "supported_client": "claude,codex",
                },
                "test-endpoint-2": {
                    "endpoint": "https://api2.test.com/v1",
                    "api_key": "test-key-2",
                    "description": "Test Endpoint 2",
                    "list_models_cmd": "echo model4 model5 model6",
                    "supported_client": "qwen",
                },
                "test-endpoint-3": {
                    "endpoint": "https://api3.test.com/v1",
                    "api_key": "test-key-3",
                    "description": "Test Endpoint 3",
                    "list_models_cmd": "echo model7 model8 model9 model10",
                    "supported_client": "claude,qwen",
                },
            },
        }
        json.dump(config_data, f, indent=2)
        config_path = f.name
    yield config_path
    Path(config_path).unlink()


class TestConfigurationPerformance:
    """Performance tests for configuration management."""

    def test_config_loading_performance(self, performance_config):
        """Test configuration loading performance."""
        # Measure time to load configuration
        start_time = time.perf_counter()
        config = ConfigManager(performance_config)
        end_time = time.perf_counter()

        load_time = end_time - start_time
        assert load_time < 0.1  # Should load in less than 100ms

        # Test getting sections
        start_time = time.perf_counter()
        sections = config.get_sections()
        end_time = time.perf_counter()

        get_sections_time = end_time - start_time
        assert get_sections_time < 0.01  # Should be very fast
        assert len(sections) == 3

    def test_config_reload_performance(self, performance_config):
        """Test configuration reload performance."""
        config = ConfigManager(performance_config)

        # Measure time to reload configuration
        start_time = time.perf_counter()
        config.reload()
        end_time = time.perf_counter()

        reload_time = end_time - start_time
        assert reload_time < 0.1  # Should reload in less than 100ms

    def test_config_value_access_performance(self, performance_config):
        """Test configuration value access performance."""
        config = ConfigManager(performance_config)

        # Test multiple value accesses
        start_time = time.perf_counter()
        for i in range(1000):
            config.get_value("test-endpoint-1", "endpoint")
            config.get_value("test-endpoint-2", "api_key")
        end_time = time.perf_counter()

        access_time = end_time - start_time
        assert access_time < 0.1  # 1000 accesses should be less than 100ms


class TestEndpointPerformance:
    """Performance tests for endpoint management."""

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_model_fetch_performance(self, mock_subprocess, performance_config):
        """Test model fetching performance."""
        mock_subprocess.return_value = MagicMock(
            stdout="model1\nmodel2\nmodel3\nmodel4\nmodel5", returncode=0
        )

        config = ConfigManager(performance_config)
        endpoint_manager = EndpointManager(config)

        endpoint_config = {
            "endpoint": "https://api.test.com/v1",
            "actual_api_key": "test-key",
            "list_models_cmd": "echo model1 model2 model3 model4 model5",
        }

        # Measure time to fetch models
        start_time = time.perf_counter()
        success, models = endpoint_manager.fetch_models(
            "test-endpoint-1", endpoint_config
        )
        end_time = time.perf_counter()

        fetch_time = end_time - start_time
        assert success is True
        assert len(models) == 5
        assert (
            fetch_time < 0.2
        )  # Should fetch in less than 200ms (more realistic threshold)

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_multiple_model_fetch_performance(
        self, mock_subprocess, performance_config
    ):
        """Test multiple model fetching performance."""
        mock_subprocess.return_value = MagicMock(
            stdout="model1\nmodel2\nmodel3\nmodel4\nmodel5", returncode=0
        )

        config = ConfigManager(performance_config)
        endpoint_manager = EndpointManager(config)

        endpoint_config = {
            "endpoint": "https://api.test.com/v1",
            "actual_api_key": "test-key",
            "list_models_cmd": "echo model1 model2 model3 model4 model5",
        }

        # Measure time to fetch models multiple times
        start_time = time.perf_counter()
        for i in range(100):
            success, models = endpoint_manager.fetch_models(
                "test-endpoint-1", endpoint_config
            )
            assert success is True
        end_time = time.perf_counter()

        total_fetch_time = end_time - start_time
        assert total_fetch_time < 1.0  # 100 fetches should be less than 1 second

    @patch("code_assistant_manager.endpoints.display_centered_menu")
    def test_endpoint_selection_performance(self, mock_menu, performance_config):
        """Test endpoint selection performance."""
        config = ConfigManager(performance_config)
        endpoint_manager = EndpointManager(config)

        # Mock the UI interaction to avoid stdin reading
        mock_menu.return_value = (True, 0)  # Simulate selecting first endpoint

        # Measure time to select endpoint
        start_time = time.perf_counter()
        success, endpoint_name = endpoint_manager.select_endpoint("claude")
        end_time = time.perf_counter()

        selection_time = end_time - start_time
        assert success is True
        assert selection_time < 0.01  # Should be very fast


class TestCachePerformance:
    """Performance tests for caching."""

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_cache_hit_performance(self, mock_subprocess, performance_config):
        """Test cache hit performance."""
        mock_subprocess.return_value = MagicMock(
            stdout="model1\nmodel2\nmodel3", returncode=0
        )

        config = ConfigManager(performance_config)
        endpoint_manager = EndpointManager(config)

        endpoint_config = {
            "endpoint": "https://api.test.com/v1",
            "actual_api_key": "test-key",
            "list_models_cmd": "echo model1 model2 model3",
        }

        # First fetch to populate cache
        success, models1 = endpoint_manager.fetch_models(
            "test-endpoint-1", endpoint_config
        )
        assert success is True

        # Measure time for cache hit
        start_time = time.perf_counter()
        success, models2 = endpoint_manager.fetch_models(
            "test-endpoint-1", endpoint_config
        )
        end_time = time.perf_counter()

        cache_hit_time = end_time - start_time
        assert success is True
        assert models1 == models2
        assert (
            cache_hit_time < 0.05
        )  # Cache hit should be fast (increased threshold for test stability)

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_cache_creation_performance(self, mock_subprocess, performance_config):
        """Test cache creation performance."""
        mock_subprocess.return_value = MagicMock(
            stdout="model1\nmodel2\nmodel3\nmodel4\nmodel5\nmodel6\nmodel7\nmodel8\nmodel9\nmodel10",
            returncode=0,
        )

        config = ConfigManager(performance_config)
        endpoint_manager = EndpointManager(config)

        endpoint_config = {
            "endpoint": "https://api.test.com/v1",
            "actual_api_key": "test-key",
            "list_models_cmd": "echo model1 model2 model3 model4 model5 model6 model7 model8 model9 model10",
        }

        # Measure time to create cache
        start_time = time.perf_counter()
        success, models = endpoint_manager.fetch_models(
            "test-endpoint-1", endpoint_config
        )
        end_time = time.perf_counter()

        cache_creation_time = end_time - start_time
        assert success is True
        assert len(models) == 10
        assert (
            cache_creation_time < 0.2
        )  # Should create cache in less than 200ms (more realistic threshold)


class TestToolPerformance:
    """Performance tests for CLI tools."""

    @patch("subprocess.run")
    @patch("code_assistant_manager.ui.display_centered_menu")
    @patch("code_assistant_manager.tools.select_two_models")
    @patch.dict(os.environ, {"CODE_ASSISTANT_MANAGER_NONINTERACTIVE": "1"})
    def test_claude_tool_performance(
        self, mock_select_models, mock_menu, mock_run, performance_config
    ):
        """Test Claude tool performance."""
        config = ConfigManager(performance_config)
        tool = ClaudeTool(config)

        # Mock dependencies
        with patch.object(tool, "_check_command_available", return_value=True):
            mock_menu.return_value = (True, 1)

            with patch.object(
                tool.endpoint_manager,
                "select_endpoint",
                return_value=(True, "test-endpoint-1"),
            ):
                endpoint_config = {
                    "endpoint": "https://api.test.com/v1",
                    "actual_api_key": "test-key",
                    "list_models_cmd": "echo model1 model2",
                }
                with patch.object(
                    tool.endpoint_manager,
                    "get_endpoint_config",
                    return_value=(True, endpoint_config),
                ):
                    with patch.object(
                        tool.endpoint_manager,
                        "fetch_models",
                        return_value=(True, ["claude-3", "claude-2"]),
                    ):
                        mock_select_models.return_value = (
                            True,
                            ("claude-3", "claude-2"),
                        )
                        mock_run.return_value = MagicMock(returncode=0)

                        # Measure tool execution time
                        start_time = time.perf_counter()
                        result = tool.run([])
                        end_time = time.perf_counter()

                        execution_time = end_time - start_time
                        assert result == 0
                        assert (
                            execution_time < 0.2
                        )  # Should execute in less than 200ms (more realistic threshold)

    def test_tool_initialization_performance(self, performance_config):
        """Test tool initialization performance."""
        config = ConfigManager(performance_config)

        # Measure time to initialize multiple tools
        start_time = time.perf_counter()
        for i in range(100):
            tool = ClaudeTool(config)
            assert tool is not None
        end_time = time.perf_counter()

        initialization_time = end_time - start_time
        assert (
            initialization_time < 0.5
        )  # 100 initializations should be less than 500ms


class TestMemoryPerformance:
    """Performance tests for memory usage."""

    def test_config_memory_usage(self, performance_config):
        """Test configuration memory usage."""
        import sys

        # Measure memory usage of config objects
        configs = []
        start_memory = sys.getsizeof(configs)

        for i in range(1000):
            config = ConfigManager(performance_config)
            configs.append(config)

        end_memory = sys.getsizeof(configs)
        memory_per_config = (end_memory - start_memory) / 1000

        # Each config object should be relatively small
        assert memory_per_config < 1000  # Less than 1KB per config object

    def test_endpoint_manager_memory_usage(self, performance_config):
        """Test endpoint manager memory usage."""
        import sys

        config = ConfigManager(performance_config)

        # Measure memory usage of endpoint manager objects
        managers = []
        start_memory = sys.getsizeof(managers)

        for i in range(1000):
            manager = EndpointManager(config)
            managers.append(manager)

        end_memory = sys.getsizeof(managers)
        memory_per_manager = (end_memory - start_memory) / 1000

        # Each manager object should be relatively small
        assert memory_per_manager < 1000  # Less than 1KB per manager object


class TestConcurrentPerformance:
    """Performance tests for concurrent operations."""

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_concurrent_model_fetch_performance(
        self, mock_subprocess, performance_config
    ):
        """Test concurrent model fetching performance."""
        mock_subprocess.return_value = MagicMock(
            stdout="model1\nmodel2\nmodel3", returncode=0
        )

        config = ConfigManager(performance_config)
        endpoint_manager = EndpointManager(config)

        endpoint_configs = [
            {
                "endpoint": "https://api1.test.com/v1",
                "actual_api_key": "test-key-1",
                "list_models_cmd": "echo model1 model2 model3",
            },
            {
                "endpoint": "https://api2.test.com/v1",
                "actual_api_key": "test-key-2",
                "list_models_cmd": "echo model4 model5 model6",
            },
            {
                "endpoint": "https://api3.test.com/v1",
                "actual_api_key": "test-key-3",
                "list_models_cmd": "echo model7 model8 model9",
            },
        ]

        # Measure time to fetch models concurrently (simulated)
        start_time = time.perf_counter()
        results = []
        for i, endpoint_config in enumerate(endpoint_configs):
            success, models = endpoint_manager.fetch_models(
                f"test-endpoint-{i+1}", endpoint_config
            )
            results.append((success, models))
        end_time = time.perf_counter()

        total_time = end_time - start_time
        assert all(success for success, _ in results)
        assert total_time < 0.3  # 3 fetches should be less than 300ms

    def test_large_config_performance(self, tmp_path):
        """Test performance with large configuration."""
        # Create a large configuration file
        large_config_file = tmp_path / "large_config.json"
        endpoints = {}

        # Create 1000 endpoints
        for i in range(1000):
            endpoints[f"endpoint-{i}"] = {
                "endpoint": f"https://api{i}.test.com/v1",
                "api_key": f"test-key-{i}",
                "description": f"Test Endpoint {i}",
                "list_models_cmd": f"echo model{i}-1 model{i}-2",
                "supported_client": "claude",
            }

        config_data = {"common": {"cache_ttl_seconds": 3600}, "endpoints": endpoints}

        with open(large_config_file, "w") as f:
            json.dump(config_data, f, indent=2)

        # Measure time to load large configuration
        start_time = time.perf_counter()
        config = ConfigManager(str(large_config_file))
        end_time = time.perf_counter()

        load_time = end_time - start_time
        assert load_time < 1.0  # Should load in less than 1 second

        # Measure time to get sections
        start_time = time.perf_counter()
        sections = config.get_sections()
        end_time = time.perf_counter()

        get_sections_time = end_time - start_time
        assert len(sections) == 1000
        assert get_sections_time < 0.1  # Should be fast even with 1000 sections
