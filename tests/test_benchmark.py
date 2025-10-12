"""Benchmark tests for code_assistant_manager."""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.endpoints import EndpointManager
from code_assistant_manager.tools import ClaudeTool


@pytest.fixture
def benchmark_config():
    """Create a config file for benchmark testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_data = {
            "common": {"cache_ttl_seconds": 3600},
            "endpoints": {
                "benchmark-endpoint": {
                    "endpoint": "https://api.benchmark.com/v1",
                    "api_key": "benchmark-key",
                    "description": "Benchmark Endpoint",
                    "list_models_cmd": "echo model1 model2 model3 model4 model5",
                    "supported_client": "claude",
                }
            },
        }
        json.dump(config_data, f, indent=2)
        config_path = f.name
    yield config_path
    Path(config_path).unlink()


class TestBenchmark:
    """Benchmark tests for performance-critical operations."""

    def test_config_loading_benchmark(self, benchmark, benchmark_config):
        """Benchmark configuration loading."""

        def load_config():
            return ConfigManager(benchmark_config)

        config = benchmark(load_config)
        assert config is not None

    def test_config_reload_benchmark(self, benchmark, benchmark_config):
        """Benchmark configuration reloading."""
        config = ConfigManager(benchmark_config)

        def reload_config():
            config.reload()

        benchmark(reload_config)

    def test_endpoint_selection_benchmark(self, benchmark, benchmark_config):
        """Benchmark endpoint selection."""
        config = ConfigManager(benchmark_config)
        endpoint_manager = EndpointManager(config)

        def select_endpoint():
            # This will fail in tests but we're benchmarking the method overhead
            try:
                return endpoint_manager.select_endpoint("claude")
            except:
                return (False, None)

        result = benchmark(select_endpoint)
        # We're just benchmarking the method call overhead

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_model_fetch_benchmark(self, mock_subprocess, benchmark, benchmark_config):
        """Benchmark model fetching."""
        mock_subprocess.return_value = MagicMock(
            stdout="model1\nmodel2\nmodel3\nmodel4\nmodel5", returncode=0
        )

        config = ConfigManager(benchmark_config)
        endpoint_manager = EndpointManager(config)

        endpoint_config = {
            "endpoint": "https://api.benchmark.com/v1",
            "actual_api_key": "benchmark-key",
            "list_models_cmd": "echo model1 model2 model3 model4 model5",
        }

        def fetch_models():
            return endpoint_manager.fetch_models("benchmark-endpoint", endpoint_config)

        success, models = benchmark(fetch_models)
        assert success is True
        assert len(models) == 5

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_cache_hit_benchmark(self, mock_subprocess, benchmark, benchmark_config):
        """Benchmark cache hit performance."""
        mock_subprocess.return_value = MagicMock(
            stdout="model1\nmodel2\nmodel3", returncode=0
        )

        config = ConfigManager(benchmark_config)
        endpoint_manager = EndpointManager(config)

        endpoint_config = {
            "endpoint": "https://api.benchmark.com/v1",
            "actual_api_key": "benchmark-key",
            "list_models_cmd": "echo model1 model2 model3",
        }

        # First fetch to populate cache
        endpoint_manager.fetch_models("benchmark-endpoint", endpoint_config)

        def fetch_from_cache():
            return endpoint_manager.fetch_models("benchmark-endpoint", endpoint_config)

        success, models = benchmark(fetch_from_cache)
        assert success is True
        assert len(models) == 3

    def test_config_value_access_benchmark(self, benchmark, benchmark_config):
        """Benchmark configuration value access."""
        config = ConfigManager(benchmark_config)

        def get_value():
            return config.get_value("benchmark-endpoint", "endpoint")

        endpoint_url = benchmark(get_value)
        assert endpoint_url == "https://api.benchmark.com/v1"

    def test_multiple_config_value_access_benchmark(self, benchmark, benchmark_config):
        """Benchmark multiple configuration value accesses."""
        config = ConfigManager(benchmark_config)

        def get_multiple_values():
            values = []
            for i in range(100):
                values.append(config.get_value("benchmark-endpoint", "endpoint"))
                values.append(config.get_value("benchmark-endpoint", "api_key"))
            return values

        values = benchmark(get_multiple_values)
        assert len(values) == 200
        assert all(v is not None for v in values)

    @patch("subprocess.run")
    @patch("code_assistant_manager.ui.display_centered_menu")
    @patch("code_assistant_manager.tools.select_two_models")
    @patch.dict(os.environ, {"CODE_ASSISTANT_MANAGER_NONINTERACTIVE": "1"})
    def test_tool_execution_benchmark(
        self, mock_select_models, mock_menu, mock_run, benchmark, benchmark_config
    ):
        """Benchmark tool execution."""
        config = ConfigManager(benchmark_config)
        tool = ClaudeTool(config)

        # Mock dependencies
        with patch.object(tool, "_check_command_available", return_value=True):
            mock_menu.return_value = (True, 1)

            with patch.object(
                tool.endpoint_manager,
                "select_endpoint",
                return_value=(True, "benchmark-endpoint"),
            ):
                endpoint_config = {
                    "endpoint": "https://api.benchmark.com/v1",
                    "actual_api_key": "benchmark-key",
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

                        def run_tool():
                            return tool.run([])

                        result = benchmark(run_tool)
                        assert result == 0

    def test_tool_initialization_benchmark(self, benchmark, benchmark_config):
        """Benchmark tool initialization."""
        config = ConfigManager(benchmark_config)

        def create_tool():
            return ClaudeTool(config)

        tool = benchmark(create_tool)
        assert tool is not None

    def test_cache_creation_benchmark(self, benchmark, benchmark_config):
        """Benchmark cache creation."""
        with patch(
            "code_assistant_manager.endpoints.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                stdout="model1\nmodel2\nmodel3\nmodel4\nmodel5", returncode=0
            )

            config = ConfigManager(benchmark_config)
            endpoint_manager = EndpointManager(config)

            endpoint_config = {
                "endpoint": "https://api.benchmark.com/v1",
                "actual_api_key": "benchmark-key",
                "list_models_cmd": "echo model1 model2 model3 model4 model5",
            }

            def create_cache():
                return endpoint_manager.fetch_models(
                    "benchmark-endpoint", endpoint_config
                )

            success, models = benchmark(create_cache)
            assert success is True
            assert len(models) == 5


class TestMemoryBenchmark:
    """Memory benchmark tests."""

    def test_config_memory_benchmark(self, benchmark, benchmark_config):
        """Benchmark configuration memory usage."""

        def create_configs():
            configs = []
            for i in range(100):
                configs.append(ConfigManager(benchmark_config))
            return configs

        configs = benchmark(create_configs)
        assert len(configs) == 100

    def test_endpoint_manager_memory_benchmark(self, benchmark, benchmark_config):
        """Benchmark endpoint manager memory usage."""
        config = ConfigManager(benchmark_config)

        def create_managers():
            managers = []
            for i in range(100):
                managers.append(EndpointManager(config))
            return managers

        managers = benchmark(create_managers)
        assert len(managers) == 100

    def test_tool_memory_benchmark(self, benchmark, benchmark_config):
        """Benchmark tool memory usage."""
        config = ConfigManager(benchmark_config)

        def create_tools():
            tools = []
            for i in range(100):
                tools.append(ClaudeTool(config))
            return tools

        tools = benchmark(create_tools)
        assert len(tools) == 100


class TestScalabilityBenchmark:
    """Scalability benchmark tests."""

    def test_scalable_config_loading(self, benchmark, tmp_path):
        """Benchmark config loading with different sizes."""

        def create_config_with_endpoints(count):
            endpoints = {}
            for i in range(count):
                endpoints[f"endpoint-{i}"] = {
                    "endpoint": f"https://api{i}.test.com/v1",
                    "api_key": f"key-{i}",
                    "description": f"Endpoint {i}",
                    "list_models_cmd": f"echo model{i}-1 model{i}-2",
                    "supported_client": "claude",
                }

            config_data = {
                "common": {"cache_ttl_seconds": 3600},
                "endpoints": endpoints,
            }

            config_file = tmp_path / f"config_{count}.json"
            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            return str(config_file)

        def load_configs():
            config_10 = ConfigManager(create_config_with_endpoints(10))
            config_100 = ConfigManager(create_config_with_endpoints(100))
            config_1000 = ConfigManager(create_config_with_endpoints(1000))
            return config_10, config_100, config_1000

        # Benchmark all config loading operations together
        config_10, config_100, config_1000 = benchmark.pedantic(
            load_configs, iterations=5, rounds=3
        )

        assert config_10 is not None
        assert config_100 is not None
        assert config_1000 is not None

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_scalable_model_fetching(
        self, mock_subprocess, benchmark, benchmark_config
    ):
        """Benchmark model fetching with different model counts."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        config = ConfigManager(benchmark_config)
        endpoint_manager = EndpointManager(config)

        endpoint_config = {
            "endpoint": "https://api.benchmark.com/v1",
            "actual_api_key": "benchmark-key",
        }

        def fetch_all_model_lists():
            # Small model list
            mock_subprocess.return_value.stdout = "model1\nmodel2\nmodel3"
            endpoint_config["list_models_cmd"] = "echo model1 model2 model3"
            success_small, models_small = endpoint_manager.fetch_models(
                "benchmark-endpoint", endpoint_config
            )

            # Medium model list
            mock_subprocess.return_value.stdout = "\n".join(
                [f"model{i}" for i in range(1, 21)]
            )
            endpoint_config["list_models_cmd"] = "echo " + " ".join(
                [f"model{i}" for i in range(1, 21)]
            )
            success_medium, models_medium = endpoint_manager.fetch_models(
                "benchmark-endpoint", endpoint_config
            )

            # Large model list
            mock_subprocess.return_value.stdout = "\n".join(
                [f"model{i}" for i in range(1, 101)]
            )
            endpoint_config["list_models_cmd"] = "echo " + " ".join(
                [f"model{i}" for i in range(1, 101)]
            )
            success_large, models_large = endpoint_manager.fetch_models(
                "benchmark-endpoint", endpoint_config
            )

            return (
                (success_small, models_small),
                (success_medium, models_medium),
                (success_large, models_large),
            )

        # Benchmark all fetch operations together
        result_small, result_medium, result_large = benchmark.pedantic(
            fetch_all_model_lists, iterations=5, rounds=3
        )
        success_small, models_small = result_small
        success_medium, models_medium = result_medium
        success_large, models_large = result_large

        assert success_small is True
        assert success_medium is True
        assert success_large is True
        assert len(models_small) == 3
        assert len(models_medium) == 20
        assert len(models_large) == 100
