# Blackbox AI CLI Integration

This document describes the integration of Blackbox AI CLI into the Code Assistant Manager (CAM).

## Overview

Blackbox AI CLI is an AI-powered terminal assistant that provides coding assistance, project creation, debugging, and code improvements directly from the command line. CAM now provides full support for Blackbox CLI with provider and model selection capabilities.

## Installation

Blackbox CLI is installed automatically via CAM when you first launch it:

```bash
cam launch
# Select "Blackbox" from the menu
```

The installation command:
```bash
curl -fsSL https://shell.blackbox.ai/api/scripts/blackbox-cli-v2/download.sh | bash
```

## Configuration

### 1. Provider Configuration

Add a Blackbox provider to your `~/.config/code-assistant-manager/providers.json`:

```json
{
  "endpoints": {
    "blackbox-official": {
      "endpoint": "https://api.blackbox.ai",
      "api_key_env": "BLACKBOX_API_KEY",
      "list_models_cmd": "echo 'blackboxai/anthropic/claude-sonnet-4.5\nblackboxai/anthropic/claude-opus-4.5\nblackboxai/anthropic/claude-sonnet-4\nblackboxai/anthropic/claude-opus-4\nblackboxai/google/gemini-2.5-flash\nblackboxai/meta-llama/llama-3.3-70b-instruct\nblackboxai/openai/gpt-4o\nblackboxai/x-ai/grok-code-fast-1:free'",
      "use_proxy": false,
      "description": "Blackbox AI Official API",
      "supported_client": "blackbox"
    }
  }
}
```

### 2. API Key Setup

Set your Blackbox API key as an environment variable:

```bash
export BLACKBOX_API_KEY="your-api-key-here"
```

Or add it to your `~/.config/code-assistant-manager/.env` file:

```env
BLACKBOX_API_KEY=your-api-key-here
```

Get your API key from: https://app.blackbox.ai/dashboard

### 3. Available Models

Blackbox AI supports multiple AI model providers:

**Anthropic Claude Models:**
- `blackboxai/anthropic/claude-sonnet-4.5` (recommended)
- `blackboxai/anthropic/claude-opus-4.5`
- `blackboxai/anthropic/claude-sonnet-4`
- `blackboxai/anthropic/claude-opus-4`

**Google Gemini Models:**
- `blackboxai/google/gemini-2.5-flash`

**Meta Llama Models:**
- `blackboxai/meta-llama/llama-3.3-70b-instruct`

**OpenAI Models:**
- `blackboxai/openai/gpt-4o`

**X.AI Models:**
- `blackboxai/x-ai/grok-code-fast-1:free`

## Usage

### Launch via CAM

```bash
# Interactive launch menu
cam launch
# Select "Blackbox" from the menu

# Or directly
cam l blackbox
```

When you launch Blackbox via CAM:

1. **Provider Selection**: CAM will show you all configured endpoints that support Blackbox
2. **Model Selection**: Choose from available models for your selected endpoint
3. **Configuration**: CAM automatically:
   - Writes `~/.blackboxcli/settings.json` with your provider configuration
   - Sets environment variables (`BLACKBOX_API_KEY`, `BLACKBOX_API_BASE_URL`, `BLACKBOX_API_MODEL`)
   - Launches Blackbox CLI in interactive mode

### Environment Variables

CAM sets the following environment variables for Blackbox:

- `BLACKBOX_API_KEY` - Your Blackbox API key (masked in output)
- `BLACKBOX_API_BASE_URL` - The endpoint URL
- `BLACKBOX_API_MODEL` - Selected model name
- `NODE_TLS_REJECT_UNAUTHORIZED=0` - For self-signed certificate support

## Generated Configuration Files

### ~/.blackboxcli/settings.json

CAM generates a Blackbox configuration file:

```json
{
  "security": {
    "auth": {
      "selectedType": "blackbox-api",
      "selectedProvider": "blackbox",
      "blackbox": {
        "apiKey": "your-api-key",
        "baseUrl": "https://api.blackbox.ai",
        "model": "blackboxai/anthropic/claude-sonnet-4.5"
      }
    }
  },
  "model": {
    "name": "blackboxai/anthropic/claude-sonnet-4.5"
  }
}
```

## Implementation Details

### Tools Configuration (`tools.yaml`)

```yaml
blackbox:
  enabled: true
  install_cmd: curl -fsSL https://shell.blackbox.ai/api/scripts/blackbox-cli-v2/download.sh | bash
  cli_command: blackbox
  description: "Blackbox AI CLI"
  env:
    exported:
      BLACKBOX_API_KEY: "Resolved from endpoint configuration"
      BLACKBOX_API_BASE_URL: "Populated from selected endpoint"
      BLACKBOX_API_MODEL: "Model selected via CAM prompt"
      NODE_TLS_REJECT_UNAUTHORIZED: "0"
  configuration:
    required:
      endpoint: "Base URL for Blackbox-compatible API"
      list_models_cmd: "Shell command returning available models"
    optional:
      api_key_env: "Environment variable name for API key"
      supported_client: "Must include 'blackbox'"
  filesystem:
    generated:
      - "~/.blackboxcli/settings.json"
```

### Python Tool Class

The `BlackboxTool` class (`code_assistant_manager/tools/blackbox.py`) handles:

1. **Endpoint validation** - Ensures the selected endpoint supports Blackbox
2. **Model fetching** - Retrieves available models from the provider
3. **Configuration writing** - Generates `~/.blackboxcli/settings.json`
4. **Environment setup** - Configures all required environment variables
5. **CLI execution** - Launches Blackbox with proper settings

## Custom Providers

You can configure custom Blackbox-compatible providers by adding them to `providers.json`:

```json
{
  "endpoints": {
    "my-custom-blackbox": {
      "endpoint": "https://my-custom-api.example.com",
      "api_key_env": "MY_CUSTOM_API_KEY",
      "list_models_cmd": "curl -s https://my-custom-api.example.com/v1/models | jq -r '.data[].id'",
      "description": "My Custom Blackbox Provider",
      "supported_client": "blackbox"
    }
  }
}
```

## Authentication Methods

Blackbox CLI supports two authentication methods:

1. **API Key Authentication** (used by CAM):
   - Direct API key authentication
   - Configured via environment variables
   - Best for automation and CI/CD

2. **OAuth2 Device Flow**:
   - Interactive browser-based authentication
   - Managed by Blackbox CLI's `blackbox configure` command
   - Best for interactive development

CAM uses API key authentication for consistency with other tools.

## Troubleshooting

### API Key Issues

```bash
# Verify your API key is set
echo $BLACKBOX_API_KEY

# Check CAM configuration
cam doctor
```

### Model Availability

```bash
# Test model listing command
endpoint="https://api.blackbox.ai"
api_key="your-api-key"
echo 'blackboxai/anthropic/claude-sonnet-4.5
blackboxai/anthropic/claude-opus-4.5
...'
```

### Configuration File

```bash
# View current Blackbox configuration
cat ~/.blackboxcli/settings.json

# Backup existing configuration
cp ~/.blackboxcli/settings.json ~/.blackboxcli/settings.json.bak
```

## References

- **Blackbox AI**: https://blackbox.ai
- **Blackbox Dashboard**: https://app.blackbox.ai/dashboard
- **Blackbox Documentation**: https://docs.blackbox.ai/features/blackbox-cli/getting-started
- **CAM Repository**: https://github.com/Chat2AnyLLM/code-assistant-manager

## Related Documentation

- [Configuration Guide](./INSTALL.md)
- [Provider Setup](../providers.json.example)
- [CAM Quick Reference](./QUICK_REFERENCE.md)
