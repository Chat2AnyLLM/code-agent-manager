# Design Patterns Implementation Guide

This document describes the design patterns implemented in code-assistant-manager and how to use them.

## Overview

The code-assistant-manager codebase has been enhanced with industry-standard design patterns to improve maintainability, testability, and extensibility. This implementation follows the **Strangler Fig Pattern** - new patterns are added alongside existing code without breaking changes.

## Implemented Patterns

### 1. Value Objects Pattern

**Location**: `code_assistant_manager/value_objects.py`

Value objects wrap primitive types with validation and immutability.

**Available Value Objects:**
- `EndpointURL` - Validated endpoint URLs
- `APIKey` - Secure API keys with masked display
- `ModelID` - Validated model identifiers
- `EndpointName` - Validated endpoint names
- `ClientName` - Validated client names

**Example Usage:**
```python
from code_assistant_manager.value_objects import EndpointURL, APIKey, ModelID

# Create validated value objects
url = EndpointURL("https://api.example.com/v1")
api_key = APIKey("sk-1234567890abcdef")
model = ModelID("gpt-4")

# Value objects are immutable
# url.value = "other"  # Raises error!

# API keys are automatically masked
print(api_key)  # Output: sk-1...cdef
print(repr(api_key))  # Output: APIKey(***)

# Get actual value when needed
actual_key = api_key.get_value()
```

**Benefits:**
- Type safety at compile time
- Validation at creation
- Immutability prevents bugs
- Self-documenting code

---

### 2. Factory Pattern

**Location**: `code_assistant_manager/factory.py`

Centralized tool creation with registration system.

**Example Usage:**
```python
from code_assistant_manager.factory import ToolFactory, register_tool

# Register a tool using decorator
@register_tool('mytool', metadata={'description': 'My custom tool'})
class MyTool:
    def __init__(self, config):
        self.config = config

# Or register manually
ToolFactory.register('anothertool', AnotherTool)

# Create tool instances
tool = ToolFactory.create('mytool', config_manager)

# Check available tools
tools = ToolFactory.get_available_tools()
```

**Dependency Injection Container:**
```python
from code_assistant_manager.factory import ServiceContainer, get_container

# Get global container
container = get_container()

# Register services
container.register_singleton('config', ConfigManager())
container.register_factory('tool_factory', lambda: ToolFactory())

# Get services
config = container.get('config')
```

**Benefits:**
- Easy to add new tools without modifying existing code
- Plugin architecture support
- Centralized creation logic
- Better testability

---

### 3. Strategy Pattern

**Location**: `code_assistant_manager/strategies.py`

Pluggable algorithms for environment setup.

**Available Strategies:**
- `ClaudeEnvironmentStrategy`
- `CodexEnvironmentStrategy`
- `QwenEnvironmentStrategy`
- `CodeBuddyEnvironmentStrategy`
- `IfLowEnvironmentStrategy`
- `NeovateEnvironmentStrategy`
- `CopilotEnvironmentStrategy`
- `GenericEnvironmentStrategy`

**Example Usage:**
```python
from code_assistant_manager.strategies import EnvironmentStrategyFactory, ClaudeEnvironmentStrategy
from code_assistant_manager.domain_models import ExecutionContext

# Get strategy for a tool
strategy = EnvironmentStrategyFactory.get_strategy('claude')

# Or use directly
strategy = ClaudeEnvironmentStrategy()

# Setup environment
context = ExecutionContext(
    tool_name='claude',
    args=[],
    endpoint_config=endpoint_config,
    selected_models=(primary_model, secondary_model)
)
env = strategy.setup_environment(context)

# Register custom strategy
EnvironmentStrategyFactory.register_strategy('custom', CustomStrategy)
```

**Benefits:**
- Separates configuration from execution
- Easy to test different configurations
- Reduces code duplication
- Pluggable behavior

---

### 4. Chain of Responsibility Pattern

**Location**: `code_assistant_manager/validators.py`

Flexible validation pipelines.

**Available Validators:**
- `URLValidator` - Validates endpoint URLs
- `APIKeyValidator` - Validates API keys
- `ModelIDValidator` - Validates model IDs
- `ProxyValidator` - Validates proxy settings
- `BooleanValidator` - Validates boolean fields
- `RequiredFieldsValidator` - Validates required fields
- `CommandValidator` - Validates command strings

**Example Usage:**
```python
from code_assistant_manager.validators import ValidationPipeline, URLValidator, APIKeyValidator

# Build validation pipeline
pipeline = (ValidationPipeline()
    .add(URLValidator())
    .add(APIKeyValidator())
    .add(ProxyValidator()))

# Validate data
is_valid, errors = pipeline.validate(endpoint_data)

# Use predefined pipelines
pipeline = ValidationPipeline.for_endpoint_config()
is_valid, errors = pipeline.validate(endpoint_data)

# High-level validator
from code_assistant_manager.validators import ConfigValidator

validator = ConfigValidator()
is_valid, errors = validator.validate_endpoint(endpoint_data)
is_valid, errors = validator.validate_all_endpoints(all_endpoints)
```

**Benefits:**
- Flexible validation pipeline
- Easy to add/remove validators
- Single responsibility per validator
- Reorderable validators

---

### 5. Repository Pattern

**Location**: `code_assistant_manager/repositories.py`

Abstract data access layer.

**Available Repositories:**
- `JsonConfigRepository` - JSON file-based configuration
- `FileCacheRepository` - File-based model cache
- `InMemoryCacheRepository` - In-memory cache (for testing)

**Example Usage:**
```python
from code_assistant_manager.repositories import JsonConfigRepository, FileCacheRepository
from pathlib import Path

# Create repositories
config_repo = JsonConfigRepository(
    file_path=Path('providers.json'),
    env_resolver=resolve_api_key_function
)

cache_repo = FileCacheRepository(
    cache_dir=Path.home() / '.cache' / 'code-assistant-manager',
    ttl_seconds=86400
)

# Use repositories
endpoint = config_repo.find_by_name('litellm')
all_endpoints = config_repo.find_all()
common_config = config_repo.get_common_config()

# Cache operations
models = cache_repo.get_models('endpoint_name')
cache_repo.save_models('endpoint_name', model_list)
cache_repo.clear('endpoint_name')
```

**Benefits:**
- Abstraction over data storage
- Easy to swap implementations
- Better testability with mocks
- Consistent API

---

### 6. Domain Models

**Location**: `code_assistant_manager/domain_models.py`

Rich domain objects that encapsulate business logic.

**Available Models:**
- `ProxySettings` - Proxy configuration
- `EndpointConfig` - Complete endpoint configuration
- `ExecutionContext` - Tool execution context
- `ExecutionResult` - Execution result
- `ToolMetadata` - Tool metadata

**Example Usage:**
```python
from code_assistant_manager.domain_models import EndpointConfig, ExecutionContext
from code_assistant_manager.value_objects import EndpointName, EndpointURL

# Create domain objects
endpoint_config = EndpointConfig(
    name=EndpointName('litellm'),
    url=EndpointURL('https://api.example.com'),
    description='LiteLLM API',
    supported_clients=[ClientName('claude'), ClientName('codex')],
    api_key=APIKey('sk-1234567890abcdef')
)

# Use rich domain methods
if endpoint_config.supports_client('claude'):
    print(f"Supports Claude: {endpoint_config.url}")

# Build execution context
context = (ExecutionContextBuilder('claude')
    .with_args(['--help'])
    .with_endpoint_config(endpoint_config)
    .with_selected_model(ModelID('gpt-4'))
    .build())
```

**Benefits:**
- Self-documenting code
- Business logic co-located with data
- Type-safe operations
- Immutable where appropriate

---

### 7. Service Layer

**Location**: `code_assistant_manager/services.py`

Separates business logic from infrastructure and UI.

**Available Services:**
- `ConfigurationService` - Configuration operations
- `ModelService` - Model operations
- `ToolInstallationService` - Tool installation
- `ExecutionContextBuilder` - Context building

**Example Usage:**
```python
from code_assistant_manager.services import ConfigurationService, ModelService

# Create services
config_service = ConfigurationService(config_repository)
model_service = ModelService(cache_repository, model_fetcher_func)

# Use services
endpoint = config_service.get_endpoint('litellm')
endpoints = config_service.get_endpoints_for_client('claude')

success, models = model_service.get_available_models(
    endpoint_name='litellm',
    endpoint_config=endpoint,
    use_cache=True
)

# Clear cache
model_service.clear_cache('litellm')
```

**Benefits:**
- Clear separation of concerns
- Business logic independent of UI
- Easier to test
- Reusable across different interfaces

---

## Migration Guide

### For New Code

Use the new patterns directly:

```python
from code_assistant_manager.value_objects import EndpointURL, APIKey
from code_assistant_manager.domain_models import EndpointConfig
from code_assistant_manager.factory import ToolFactory, register_tool

@register_tool('newtool')
class NewTool:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service

    def run(self, args):
        endpoint = self.config_service.get_endpoint('api')
        # Use validated value objects
        print(f"Connecting to {endpoint.url}")
```

### For Existing Code

The existing code continues to work unchanged. Gradually migrate by:

1. **Start with value objects** - Wrap primitives where validation matters
2. **Use services** - Extract business logic to service layer
3. **Apply strategies** - Move environment setup to strategies
4. **Add validation** - Use validation pipelines for input validation
5. **Use repositories** - Abstract data access

Example migration:

```python
# Old code
endpoint_url = config.get('endpoint')  # string
if not validate_url(endpoint_url):
    raise ValueError("Invalid URL")

# New code
from code_assistant_manager.value_objects import EndpointURL
endpoint_url = EndpointURL(config.get('endpoint'))  # Validated!
```

---

## Testing

All patterns include comprehensive unit tests:

```bash
# Run all unit tests
python -m pytest tests/unit/ -v

# Run specific test file
python -m pytest tests/unit/test_value_objects.py -v

# Run with coverage
python -m pytest tests/unit/ --cov=code_assistant_manager --cov-report=html
```

**Test Files:**
- `tests/unit/test_value_objects.py` - Value object tests
- `tests/unit/test_factory.py` - Factory pattern tests
- `tests/unit/test_validators.py` - Validation tests
- More tests to come...

---

## Best Practices

### 1. Use Value Objects for Validation

```python
# Bad
def connect(url: str, api_key: str):
    if not url.startswith('https://'):
        raise ValueError("Invalid URL")
    # ...

# Good
def connect(url: EndpointURL, api_key: APIKey):
    # Already validated!
    # ...
```

### 2. Inject Dependencies

```python
# Bad
class MyService:
    def __init__(self):
        self.config = ConfigManager()  # Hard-coded dependency

# Good
class MyService:
    def __init__(self, config: ConfigManager):
        self.config = config  # Injected dependency
```

### 3. Use Services for Business Logic

```python
# Bad - UI code mixed with business logic
def handle_command():
    config = load_config()
    models = fetch_models()
    model = select_model(models)
    execute(model)

# Good - Business logic in service
service = ModelService(cache_repo)
success, models = service.get_available_models(endpoint)
```

### 4. Validate at Boundaries

```python
# Bad - Validation scattered throughout
def process_data(data):
    if not data.get('url'):
        raise ValueError()
    # ... more code ...
    if not data.get('key'):
        raise ValueError()

# Good - Validation pipeline at boundary
pipeline = ValidationPipeline.for_endpoint_config()
is_valid, errors = pipeline.validate(data)
if not is_valid:
    handle_errors(errors)
    return
process_valid_data(data)
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                     CLI Layer                        │
│  (cli.py, main entry points)                        │
└───────────────┬─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────┐
│                  Service Layer                       │
│  ConfigurationService, ModelService, etc.           │
│  (services.py)                                      │
└───────────────┬─────────────────────────────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
┌──────────────┐  ┌──────────────┐
│  Repository  │  │  Strategies  │
│   Layer      │  │    Layer     │
│ (repos.py)   │  │ (strats.py)  │
└──────┬───────┘  └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│              Domain Model Layer                      │
│  Value Objects, Domain Models                       │
│  (value_objects.py, domain_models.py)               │
└─────────────────────────────────────────────────────┘
```

---

## Further Reading

- [CODEBASE_ANALYSIS.md](CODEBASE_ANALYSIS.md) - Complete analysis and recommendations
- [Gang of Four Design Patterns](https://en.wikipedia.org/wiki/Design_Patterns)
- [Martin Fowler - Patterns of Enterprise Application Architecture](https://martinfowler.com/books/eaa.html)
- [Domain-Driven Design](https://en.wikipedia.org/wiki/Domain-driven_design)

---

## Contributing

When adding new features:

1. **Use value objects** for validated primitives
2. **Create domain models** for business entities
3. **Write services** for business logic
4. **Use strategies** for algorithms
5. **Write tests** for everything
6. **Update this doc** with examples

---

## Support

For questions or issues with the design patterns:
1. Check the unit tests for usage examples
2. Review CODEBASE_ANALYSIS.md for detailed explanations
3. Create an issue on GitHub
