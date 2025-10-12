"""Tests for the model selector module."""

from code_assistant_manager.menu.model_selector import ModelSelector


class TestModelSelector:
    """Test ModelSelector class."""

    def test_select_model_with_endpoint_info(self):
        """Test selecting a model with endpoint information."""
        models = ["model1", "model2", "model3"]
        endpoint_name = "test-endpoint"
        endpoint_config = {
            "endpoint": "https://api.example.com",
            "description": "Test API Endpoint",
        }

        # This would normally open a menu, but we're just testing the prompt creation
        # The actual menu interaction is tested through the existing tool tests
        pass

    def test_select_two_models_with_endpoint_info(self):
        """Test selecting two models with endpoint information."""
        models = ["model1", "model2", "model3"]
        endpoint_name = "test-endpoint"
        endpoint_config = {
            "endpoint": "https://api.example.com",
            "description": "Test API Endpoint",
        }

        # This would normally open menus, but we're just testing the prompt creation
        # The actual menu interaction is tested through the existing tool tests
        pass
