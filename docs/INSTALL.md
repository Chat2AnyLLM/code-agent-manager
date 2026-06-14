# Installation Guide

This guide covers all the ways to install and set up code-agent-manager.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Install](#quick-install)
- [Installation Methods](#installation-methods)
- [Post-Installation Setup](#post-installation-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

## System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 256MB RAM minimum, 512MB recommended
- **Storage**: 50MB free space

### Recommended Requirements
- **Python**: 3.10 or higher
- **Memory**: 1GB RAM or more
- **Storage**: 200MB free space (including dependencies)

### Dependencies
The following Python packages are automatically installed:
- `requests>=2.28.0` - HTTP client library
- `PyYAML>=6.0` - YAML configuration support
- `typer>=0.9.0` - CLI framework

## Quick Install

For the fastest installation, run:

```bash
# Install from PyPI (if available)
pip install code-agent-manager

# Or install from source
pip install git+https://github.com/Chat2AnyLLM/code-agent-manager.git

# Or use the automated installer script
./install.sh
```

## Installation Methods

### Method 1: Install from PyPI (Recommended)

If the package is published to PyPI:

```bash
# Install for current user
pip install code-agent-manager

# Or install system-wide (may require sudo)
pip install --user code-agent-manager
```

### Method 2: Install from Source

For the latest development version or if PyPI installation fails:

```bash
# Clone the repository
git clone https://github.com/Chat2AnyLLM/code-agent-manager.git
cd code-agent-manager

# Install in development mode (recommended for contributors)
pip install -e .

# Or install normally
pip install .
```

### Method 3: Install Pre-built Package

If you have a pre-built wheel or tarball:

```bash
# Install from wheel file
pip install code_assistant_manager-1.0.3-py3-none-any.whl

# Or install from source distribution
pip install code_assistant_manager-1.0.3.tar.gz
```

### Method 5: Automated Installer Script

Use the provided `install.sh` script for automated installation:

```bash
# Download and run the installer
wget https://raw.githubusercontent.com/Chat2AnyLLM/code-agent-manager/main/install.sh
chmod +x install.sh
./install.sh

# Or run directly from the repository
curl -sSL https://raw.githubusercontent.com/Chat2AnyLLM/code-agent-manager/main/install.sh | bash

# Install from source instead of PyPI
./install.sh source

# Only verify current installation
./install.sh verify
```

**Features of the installer script:**
- Automatic system requirement checks (Python 3.8+, pip)
- Colored output for better user experience
- Multiple installation methods
- Post-installation configuration setup
- Installation verification
- Helpful error messages and troubleshooting tips

## Post-Installation Setup

### 1. Verify Installation

After installation, verify that the CLI commands are available:

```bash
# Check if commands are installed
code-agent-manager --version
cam --version

# Both should output: code-agent-manager 1.0.3
```

### 2. Configuration Setup

Create basic configuration files:

```bash
# Create providers.json (copy from template)
cp code_assistant_manager/providers.json ~/.config/code-agent-manager/providers.json

# Create .env file for API keys
touch ~/.env
chmod 600 ~/.env
```

### 3. Environment Variables

Set up your API keys in the `.env` file:

```bash
# Edit your .env file
nano ~/.env

# Add your API keys (examples)
GITHUB_TOKEN=ghu_your_github_token_here
API_KEY_CLAUDE=sk-ant-your_claude_key_here
API_KEY_OPENAI=sk-your_openai_key_here
```

## Verification

### Basic Verification

```bash
# Check version
code-agent-manager --version

# Show help
code-agent-manager --help

# List available commands
cam --help
```

### Functional Verification

```bash
# Test basic functionality
code-agent-manager doctor

# Check MCP server integration
code-agent-manager mcp server list | head -10
```

### Configuration Verification

```bash
# Test configuration loading
code-agent-manager --endpoints

# Test specific endpoint
code-agent-manager --endpoints claude
```

## Troubleshooting

### Common Issues

#### 1. Command Not Found

If `code-agent-manager` or `cam` commands are not found:

```bash
# Check if package is installed
pip list | grep code-agent-manager

# Reinstall if missing
pip install -e .

# Check PATH
which code-agent-manager
echo $PATH
```

#### 2. Python Version Issues

If you encounter Python version errors:

```bash
# Check Python version
python --version
python3 --version

# Use specific Python version
python3 -m pip install code-agent-manager
python3 -m code_assistant_manager --version
```

#### 3. Permission Errors

For permission denied errors during installation:

```bash
# Install for current user only
pip install --user code-agent-manager

# Or use virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install code-agent-manager
```

#### 4. Import Errors

If you get import errors after installation:

```bash
# Reinstall in development mode
pip install -e .

# Or reinstall normally
pip uninstall code-agent-manager
pip install code-agent-manager
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Run with debug output
code-agent-manager --debug doctor
```

### Getting Help

If issues persist:

1. Check the [GitHub Issues](https://github.com/Chat2AnyLLM/code-agent-manager/issues)
2. Run diagnostics: `code-agent-manager doctor`
3. Check logs in `~/.cache/code-agent-manager/`

## Uninstallation

### Standard Uninstallation

```bash
# Uninstall the package
pip uninstall code-agent-manager

# Remove configuration files (optional)
rm -rf ~/.config/code-agent-manager
rm -rf ~/.cache/code-agent-manager
```

### Clean Uninstall

For a complete removal including all data:

```bash
# Uninstall package
pip uninstall code-agent-manager

# Remove all user data
rm -rf ~/.config/code-agent-manager/
rm -rf ~/.cache/code-agent-manager/
rm -f ~/.env.code-agent-manager*

# Remove from PATH (if manually added)
# Edit your shell profile and remove any custom PATH entries
```

### Development Uninstall

If installed in development mode:

```bash
# From the source directory
pip uninstall code-agent-manager

# Or force reinstall
pip install -e . --force-reinstall
```

## Advanced Installation

### Virtual Environment Installation

For isolated installations:

```bash
# Create virtual environment
python -m venv cam-env

# Activate environment
source cam-env/bin/activate  # Linux/macOS
# cam-env\Scripts\activate    # Windows

# Install package
pip install code-agent-manager

# Use the tool
code-agent-manager --version

# Deactivate when done
deactivate
```

### Docker Installation

For containerized usage:

```dockerfile
FROM python:3.11-slim

RUN pip install code-agent-manager

CMD ["code-agent-manager", "--help"]
```

### Conda Installation

For conda environments:

```bash
# Create conda environment
conda create -n cam python=3.11
conda activate cam

# Install package
pip install code-agent-manager
```

## Platform-Specific Notes

### Linux
- Ensure `python3-dev` packages are installed for some dependencies
- May require additional system packages: `build-essential`, `libssl-dev`

### macOS
- Use Homebrew for Python: `brew install python`
- Ensure Xcode command line tools: `xcode-select --install`

### Windows
- Use Windows Subsystem for Linux (WSL) for best compatibility
- Or use PowerShell with Python from Microsoft Store
- May need Visual Studio Build Tools for some packages

## Next Steps

After successful installation:

1. **Configure Endpoints**: Set up your AI service endpoints in `providers.json`
2. **Add API Keys**: Configure your API keys in `.env` file
3. **Test Integration**: Run `code-agent-manager doctor` to verify setup
4. **Explore Features**: Try `code-agent-manager --help` to see all options

For detailed configuration instructions, see the main [README.md](README.md) file.</content>
<parameter name="file_path">INSTALL.md
