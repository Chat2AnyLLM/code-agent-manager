# Code Assistant Manager API Documentation

This document provides detailed API documentation for the Code Assistant Manager codebase, covering all major modules and their public interfaces.

## Table of Contents

1. [CLI Module](#cli-module)
2. [Configuration Module](#configuration-module)
3. [Endpoints Module](#endpoints-module)
4. [Tools Module](#tools-module)
5. [UI Module](#ui-module)

## CLI Module

### Main Functions

#### `main()`
Main entry point for the CLI application.

**Parameters:**
- None

**Returns:**
- `int`: Exit code (0 for success, 1 for error)

#### `claude_main()`
Entry point for the 'claude' command.

**Parameters:**
- None

**Returns:**
- None (exits with sys.exit())

#### `codex_main()`
Entry point for the 'codex' command.

**Parameters:**
- None

**Returns:**
- None (exits with sys.exit())

(Similar functions exist for other tools: `droid_main()`, `qwen_main()`, `codebuddy_main()`, `copilot_main()`, `gemini_main()`, `iflow_main()`)

### Classes

#### `argparse.ArgumentParser`
Used for command-line argument parsing.

**Methods:**
- `add_argument()`: Add command-line arguments
- `parse_args()`: Parse command-line arguments

## Configuration Module

### Classes

#### `ConfigManager`
Manages providers.json file parsing and endpoint configuration.

**Constructor:**
```python
ConfigManager(config_path: Optional[str] = None)
```

**Parameters:**
- `config_path` (str, optional): Path to providers.json. If None, looks for it in standard locations.

**Methods:**

##### `reload()`
Reload configuration from file.

**Parameters:**
- None

**Returns:**
- None

##### `get_sections(exclude_common: bool = True)`
Get all endpoint sections from config.

**Parameters:**
- `exclude_common` (bool): If True, exclude the common section (always True for JSON format)

**Returns:**
- `List[str]`: List of endpoint names

##### `get_value(section: str, key: str, default: str = "")`
Get a configuration value.

**Parameters:**
- `section` (str): Section name (endpoint name or "common")
- `key` (str): Key name
- `default` (str): Default value if key not found

**Returns:**
- `str`: Configuration value or default

##### `get_endpoint_config(endpoint_name: str)`
Get full configuration for an endpoint.

**Parameters:**
- `endpoint_name` (str): Name of the endpoint

**Returns:**
- `Dict[str, str]`: Dictionary with endpoint configuration

##### `get_common_config()`
Get common configuration.

**Parameters:**
- None

**Returns:**
- `Dict[str, str]`: Dictionary with common configuration

##### `load_env_file(env_file: Optional[str] = None)`
Load environment variables from .env file.

**Parameters:**
- `env_file` (str, optional): Path to .env file. If None, looks for it in standard locations.

**Returns:**
- None

##### `validate_config()`
Validate the entire configuration.

**Parameters:**
- None

**Returns:**
- `Tuple[bool, List[str]]`: Tuple of (is_valid, list_of_errors)

### Validation Functions

#### `validate_url(url: str)`
Validate a URL.

**Parameters:**
- `url` (str): URL to validate

**Returns:**
- `bool`: True if valid, False otherwise

#### `validate_api_key(key: str)`
Validate an API key.

**Parameters:**
- `key` (str): API key to validate

**Returns:**
- `bool`: True if valid, False otherwise

#### `validate_model_id(model_id: str)`
Validate a model ID.

**Parameters:**
- `model_id` (str): Model ID to validate

**Returns:**
- `bool`: True if valid, False otherwise

#### `validate_boolean(value)`
Validate a boolean value.

**Parameters:**
- `value`: String or boolean value to validate

**Returns:**
- `bool`: True if valid, False otherwise

#### `validate_non_empty_string(value: str)`
Validate a non-empty string.

**Parameters:**
- `value` (str): String value to validate

**Returns:**
- `bool`: True if valid, False otherwise

#### `validate_command(value: str)`
Validate a command string with balanced security and functionality.

**Parameters:**
- `value` (str): Command string to validate

**Returns:**
- `bool`: True if valid, False otherwise

## Endpoints Module

### Classes

#### `EndpointManager`
Manages AI provider endpoints and model fetching.

**Constructor:**
```python
EndpointManager(config_manager: ConfigManager)
```

**Parameters:**
- `config_manager` (ConfigManager): ConfigManager instance

**Methods:**

##### `select_endpoint(client_name: Optional[str] = None)`
Display endpoint selection menu.

**Parameters:**
- `client_name` (str, optional): Optional client name to filter endpoints

**Returns:**
- `Tuple[bool, Optional[str]]`: Tuple of (success, endpoint_name)

##### `get_endpoint_config(endpoint_name: str)`
Get complete endpoint configuration.

**Parameters:**
- `endpoint_name` (str): Name of the endpoint

**Returns:**
- `Tuple[bool, Dict[str, str]]`: Tuple of (success, config_dict)

##### `fetch_models(endpoint_name: str, endpoint_config: Dict[str, str])`
Fetch available models from endpoint.

**Parameters:**
- `endpoint_name` (str): Name of the endpoint
- `endpoint_config` (Dict[str, str]): Endpoint configuration

**Returns:**
- `Tuple[bool, List[str]]`: Tuple of (success, models_list)

##### `_resolve_api_key(endpoint_name: str, endpoint_config: Dict[str, str])`
Resolve API key from various sources.

**Parameters:**
- `endpoint_name` (str): Name of the endpoint
- `endpoint_config` (Dict[str, str]): Endpoint configuration

**Returns:**
- `str`: API key or empty string

##### `_is_client_supported(endpoint_name: str, client_name: str)`
Check if endpoint supports a client.

**Parameters:**
- `endpoint_name` (str): Name of the endpoint
- `client_name` (str): Name of the client

**Returns:**
- `bool`: True if supported, False otherwise

##### `_parse_models_output(output: str)`
Parse model list from various output formats.

**Parameters:**
- `output` (str): Raw command output

**Returns:**
- `List[str]`: List of model IDs

##### `_parse_text_models(output: str)`
Parse model list from text output (space or newline separated).

**Parameters:**
- `output` (str): Raw text output

**Returns:**
- `List[str]`: List of model IDs

## Tools Module

### Classes

#### `ToolRegistry`
Registry for external CLI tools loaded from tools.yaml.

**Constructor:**
```python
ToolRegistry(config_path: Optional[Path] = None)
```

**Parameters:**
- `config_path` (Path, optional): Path to tools.yaml

**Methods:**

##### `_load()`
Load tool metadata from YAML file.

**Parameters:**
- None

**Returns:**
- `Dict[str, dict]`: Dictionary of tool metadata

##### `reload()`
Reload the registry from disk.

**Parameters:**
- None

**Returns:**
- None

##### `get_tool(tool_key: str)`
Return metadata for a tool.

**Parameters:**
- `tool_key` (str): Tool key

**Returns:**
- `dict`: Tool metadata

##### `get_install_command(tool_key: str)`
Return the install command for a tool if defined.

**Parameters:**
- `tool_key` (str): Tool key

**Returns:**
- `Optional[str]`: Install command or None

##### `is_enabled(tool_key: str)`
Check if a tool is enabled in tools.yaml.

**Parameters:**
- `tool_key` (str): Tool key to check

**Returns:**
- `bool`: True if enabled (default), False if explicitly disabled

##### `get_enabled_tools()`
Get list of all enabled tool keys.

**Parameters:**
- None

**Returns:**
- `List[str]`: List of tool keys that are enabled

#### `CLITool`
Base class for CLI tools.

**Constructor:**
```python
CLITool(config_manager: ConfigManager)
```

**Parameters:**
- `config_manager` (ConfigManager): ConfigManager instance

**Attributes:**
- `command_name` (str): Command name
- `tool_key` (Optional[str]): Tool key
- `install_description` (str): Install description

**Methods:**

##### `run(args: List[str] = [])`
Run the CLI tool.

**Parameters:**
- `args` (List[str]): Command-line arguments

**Returns:**
- `int`: Exit code

##### `_handle_error(message: str, exception: Optional[Exception] = None, exit_code: int = 1)`
Handle errors consistently across all tools.

**Parameters:**
- `message` (str): Error message to display
- `exception` (Exception, optional): Optional exception that caused the error
- `exit_code` (int): Exit code to return (default: 1)

**Returns:**
- `int`: Exit code

##### `_check_command_available(command: str)`
Check if a command is available.

**Parameters:**
- `command` (str): Command to check

**Returns:**
- `bool`: True if available, False otherwise

##### `_ensure_tool_installed(command: str, tool_key: Optional[str], desc: str)`
Ensure a CLI tool is installed, offering to install or upgrade.

**Parameters:**
- `command` (str): Command to check
- `tool_key` (str, optional): Tool key
- `desc` (str): Description of the tool

**Returns:**
- `bool`: True if installed, False otherwise

##### `_set_node_tls_env(env: dict)`
Set Node.js TLS environment variables.

**Parameters:**
- `env` (dict): Environment variables dictionary

**Returns:**
- None

##### `_setup_endpoint_and_models(client_name: str, select_multiple: bool = False)`
Set up endpoint and fetch models - common workflow for all tools.

**Parameters:**
- `client_name` (str): Name of the client (e.g., "claude", "codex")
- `select_multiple` (bool): Whether to select two models (True) or one model (False)

**Returns:**
- `Tuple[bool, Union[Tuple[Dict[str, str], str, Union[str, Tuple[str, str]]], Tuple[None, None, None]]]`: Tuple of (success, (endpoint_config, endpoint_name, model(s))) or (success, (None, None, None))

#### Tool Implementations

Each tool implementation extends `CLITool`:

- `ClaudeTool`: Claude CLI wrapper
- `CodexTool`: Codex CLI wrapper
- `QwenTool`: Qwen CLI wrapper
- `CodeBuddyTool`: CodeBuddy CLI wrapper
- `IfLowTool`: iFlow CLI wrapper
- `DroidTool`: Droid CLI wrapper
- `CopilotTool`: GitHub Copilot CLI wrapper
- `GeminiTool`: Google Gemini CLI wrapper

### Functions

#### `get_registered_tools()`
Return a mapping of CLI command names to tool classes.

**Parameters:**
- None

**Returns:**
- `Dict[str, Type[CLITool]]`: Dictionary mapping command names to tool classes

## UI Module

### Functions

#### `display_centered_menu(title: str, choices: List[str], cancel_text: str = "Cancel")`
Display a centered menu with dynamic filtering.

**Parameters:**
- `title` (str): Menu title
- `choices` (List[str]): List of choices
- `cancel_text` (str): Text for cancel option

**Returns:**
- `Tuple[bool, Optional[int]]`: Tuple of (success, selected_index)

#### `select_model(models: List[str], prompt: str)`
Select a single model from a list.

**Parameters:**
- `models` (List[str]): List of models
- `prompt` (str): Prompt text

**Returns:**
- `Tuple[bool, Optional[str]]`: Tuple of (success, selected_model)

#### `select_two_models(models: List[str], primary_prompt: str, secondary_prompt: str, cancel_text: str = "Cancel")`
Select two models from a list.

**Parameters:**
- `models` (List[str]): List of models
- `primary_prompt` (str): Prompt for primary model selection
- `secondary_prompt` (str): Prompt for secondary model selection
- `cancel_text` (str): Text for cancel option

**Returns:**
- `Tuple[bool, Optional[Tuple[str, str]]]`: Tuple of (success, (primary_model, secondary_model))

### Classes

#### `Colors`
Color constants for terminal output.

**Attributes:**
- `BLUE`: Blue color code
- `CYAN`: Cyan color code
- `GREEN`: Green color code
- `YELLOW`: Yellow color code
- `RED`: Red color code
- `RESET`: Reset color code

## Error Handling

All modules follow consistent error handling patterns:

1. **Return Codes**: Functions return appropriate error codes or boolean success indicators
2. **Exception Handling**: Proper exception handling with meaningful error messages
3. **Validation**: Input validation at entry points
4. **Logging**: Appropriate logging for debugging and monitoring

## Security Considerations

1. **Command Validation**: All shell commands are validated using `validate_command()`
2. **API Key Security**: API keys are resolved from multiple sources with environment variable precedence
3. **Input Sanitization**: All user inputs are sanitized and validated
4. **File Permissions**: Cache files are created with restrictive permissions
5. **Environment Isolation**: Proper environment variable management to prevent leakage

## Performance Considerations

1. **Caching**: Model lists are cached with configurable TTL
2. **Lazy Loading**: Configuration and tools are loaded only when needed
3. **Efficient Parsing**: Optimized parsing for different output formats
4. **Resource Management**: Proper cleanup of temporary files and resources
