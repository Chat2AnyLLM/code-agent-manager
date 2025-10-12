# Quick Start: Using Design Patterns in code-assistant-manager

## 🚀 5-Minute Quick Start

### Installation
```bash
# Already installed if you have code-assistant-manager
pip install -e .
```

### Import and Use
```python
from code_assistant_manager import (
    EndpointURL, APIKey, ModelID,      # Value Objects
    ToolFactory,                        # Factory Pattern
    ValidationPipeline,                 # Validation
)

# 1. Value Objects - Type-safe, validated primitives
url = EndpointURL("https://api.example.com")
key = APIKey("sk-1234567890abcdef")
model = ModelID("gpt-4")

print(key)  # Output: sk-1...cdef (automatically masked!)

# 2. Factory Pattern - Create tools easily
tool = ToolFactory.create('claude', config_manager)

# 3. Validation - Validate configuration
pipeline = ValidationPipeline.for_endpoint_config()
is_valid, errors = pipeline.validate({
    'endpoint': 'https://api.example.com',
    'api_key': 'sk-1234567890abcdef'
})

if is_valid:
    print("✅ Configuration is valid!")
else:
    print(f"❌ Errors: {errors}")
```

## 📚 Common Use Cases

### 1. Validate User Input
```python
from code_assistant_manager import ValidationPipeline

# Create validation pipeline
pipeline = ValidationPipeline.for_endpoint_config()

# Validate endpoint configuration
is_valid, errors = pipeline.validate(user_input)
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

### 2. Secure API Key Handling
```python
from code_assistant_manager import APIKey

# API keys are automatically validated and masked
try:
    key = APIKey(user_provided_key)
    print(f"Key accepted: {key}")  # Shows: sk-1...cdef

    # Get actual value when needed (e.g., for API calls)
    actual_key = key.get_value()
except ValueError as e:
    print(f"Invalid API key: {e}")
```

### 3. Create Custom Tools
```python
from code_assistant_manager import register_tool, ConfigurationService

@register_tool('mytool', metadata={'description': 'My custom tool'})
class MyTool:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service

    def run(self, args):
        endpoint = self.config_service.get_endpoint('my-api')
        print(f"Running with {endpoint.url}")

# Tool is automatically registered!
tool = ToolFactory.create('mytool', config_service)
```

### 4. Use Services for Business Logic
```python
from code_assistant_manager import ConfigurationService, ModelService

# Initialize services
config_service = ConfigurationService(config_repository)
model_service = ModelService(cache_repository, fetcher_func)

# Get endpoint
endpoint = config_service.get_endpoint('litellm')

# Get models (with caching)
success, models = model_service.get_available_models(
    endpoint_name='litellm',
    endpoint_config=endpoint,
    use_cache=True
)
```

## ⚡ Power Features

### Type Safety
```python
from code_assistant_manager import EndpointURL

# This works
url = EndpointURL("https://api.example.com")

# This raises ValueError immediately
url = EndpointURL("not-a-url")  # ❌ Caught at creation!
```

### Immutability
```python
from code_assistant_manager import EndpointURL

url = EndpointURL("https://api.example.com")
# url.value = "other"  # ❌ Raises FrozenInstanceError
```

### Automatic Validation
```python
from code_assistant_manager import ModelID

# Valid model IDs
model1 = ModelID("gpt-4")
model2 = ModelID("claude-3-opus")
model3 = ModelID("provider/model:version")

# Invalid model ID
model4 = ModelID("invalid model!")  # ❌ ValueError
```

### Dependency Injection
```python
from code_assistant_manager import ServiceContainer

container = ServiceContainer()

# Register services
container.register_singleton('config', config_manager)
container.register_factory('tool', lambda: ToolFactory())

# Get services
config = container.get('config')
tool = container.get('tool')
```

## 🧪 Testing with Patterns

### Mock Dependencies Easily
```python
from unittest.mock import Mock
from code_assistant_manager import ConfigurationService

def test_my_feature():
    # Mock repository
    mock_repo = Mock()
    mock_repo.find_by_name.return_value = mock_endpoint

    # Inject mock
    service = ConfigurationService(mock_repo)

    # Test with mock
    result = service.get_endpoint('test')
    assert result is not None
```

### Use In-Memory Cache for Testing
```python
from code_assistant_manager.repositories import InMemoryCacheRepository
from code_assistant_manager import ModelService

def test_model_caching():
    cache = InMemoryCacheRepository()
    service = ModelService(cache, mock_fetcher)

    # Test caching behavior
    models1 = service.get_available_models('endpoint', config)
    models2 = service.get_available_models('endpoint', config)
    assert models1 == models2
```

## 📖 Learn More

- **Full Guide**: [DESIGN_PATTERNS_README.md](DESIGN_PATTERNS_README.md)
- **Analysis**: [CODEBASE_ANALYSIS.md](CODEBASE_ANALYSIS.md)
- **Summary**: [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)

## 🎯 Next Steps

1. ✅ Try the examples above
2. ✅ Read [DESIGN_PATTERNS_README.md](DESIGN_PATTERNS_README.md) for detailed docs
3. ✅ Check unit tests for more examples
4. ✅ Start using patterns in your code!

---

**Questions?** Check the comprehensive documentation or look at the unit tests!
