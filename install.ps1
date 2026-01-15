#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Code Assistant Manager PowerShell Installation Script
.DESCRIPTION
    This script provides automated installation for Windows PowerShell users
#>

param(
    [string]$Method = "pypi",
    [switch]$Help
)

# Colors for output (PowerShell)
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Blue"
$NC = "White"

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor $BLUE
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $GREEN
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $YELLOW
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $RED
}

function Write-Header {
    param([string]$Message)
    Write-Host "=== $Message ===" -ForegroundColor $BLUE
}

function Test-Python {
    Write-Info "Checking Python version..."
    try {
        $pythonVersion = python --version 2>$null
        if ($LASTEXITCODE -ne 0) { throw "Python not found" }
        Write-Info "Python version: $pythonVersion"
    }
    catch {
        Write-Error "Python is not installed"
        exit 1
    }

    # Check Python version >= 3.8
    $versionCheck = python -c "import sys; print(sys.version_info >= (3, 8))" 2>$null
    if ($versionCheck -ne "True") {
        Write-Error "Python 3.8+ required"
        exit 1
    }
    Write-Success "Python version is compatible"
}

function Test-Pip {
    try {
        python -m pip --version >$null 2>&1
        if ($LASTEXITCODE -ne 0) { throw "pip not found" }
    }
    catch {
        Write-Error "pip is not available"
        exit 1
    }
    Write-Success "pip is available"
}

function Install-PyPI {
    Write-Header "Installing from PyPI"
    Write-Info "Installing code-assistant-manager..."

    # Check for local wheel
    $wheelFiles = Get-ChildItem "dist\*.whl" -ErrorAction SilentlyContinue
    if ($wheelFiles) {
        $wheel = $wheelFiles[0].FullName
        Write-Info "Found local wheel: $wheel -- installing (force reinstall, no deps)"
        python -m pip install --force-reinstall --no-deps $wheel
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to install local wheel"
            Install-PyPIFallback
            return
        }
        Write-Info "Installing runtime dependencies from requirements.txt via PyPI"
        python -m pip install --index-url https://pypi.org/simple -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to install dependencies from PyPI"
            Install-PyPIFallback
            return
        }
        Write-Success "Installed from local wheel and installed dependencies"
        return
    }

    # Try to build and install local wheel
    if (Install-BuildLocal) {
        return
    }

    Install-PyPIFallback
}

function Install-BuildLocal {
    Write-Header "Building local wheel"
    Write-Info "Ensuring build tools are available..."
    python -m pip install --upgrade pip setuptools wheel build
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to install build tools"
        return $false
    }

    Write-Info "Cleaning previous build artifacts..."
    Remove-Item -Recurse -Force "build", "dist" -ErrorAction SilentlyContinue
    Get-ChildItem "*.egg-info" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    Write-Info "Running build..."
    python -m build
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Local build failed"
        return $false
    }

    $wheelFiles = Get-ChildItem "dist\*.whl" -ErrorAction SilentlyContinue
    if (-not $wheelFiles) {
        Write-Warning "Build completed but no wheel found in dist/"
        return $false
    }

    $wheel = $wheelFiles[0].FullName
    Write-Info "Built wheel: $wheel -- installing (no deps)"
    python -m pip install --force-reinstall --no-deps $wheel
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to install built wheel"
        return $false
    }

    Write-Info "Installing runtime dependencies from requirements.txt via PyPI"
    python -m pip install --index-url https://pypi.org/simple -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to install dependencies from PyPI after build"
        return $false
    }

    Write-Success "Installed from built wheel and installed dependencies"
    return $true
}

function Install-PyPIFallback {
    python -m pip install --index-url https://pypi.org/simple code-assistant-manager
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "PyPI install failed; will attempt source install"
        Install-Source
        return
    }
    Write-Success "Installed from PyPI"
}

function Install-Source {
    Write-Header "Installing from source"
    Write-Info "Cloning repository..."

    # Check if git is available
    try {
        git --version >$null 2>&1
        if ($LASTEXITCODE -ne 0) { throw "git not found" }
    }
    catch {
        Write-Error "Git is not available for source installation"
        exit 1
    }

    $tempDir = Join-Path $env:TEMP "cam-install-$([System.Guid]::NewGuid().ToString().Substring(0,8))"
    git clone https://github.com/Chat2AnyLLM/code-assistant-manager.git $tempDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to clone repository"
        exit 1
    }

    Push-Location $tempDir
    Write-Info "Installing in development mode..."
    python -m pip install -e .
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install from source"
        Pop-Location
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
        exit 1
    }
    Write-Success "Installed from source"
    Pop-Location
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
}

function Setup-Config {
    Write-Header "Setting up configuration"

    $configDir = Join-Path $env:USERPROFILE ".config\code-assistant-manager"
    if (-not (Test-Path $configDir)) {
        New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    }

    # Create Windows-specific config directories
    if ($env:APPDATA) {
        $appDataConfigDir = Join-Path $env:APPDATA "code-assistant-manager"
        if (-not (Test-Path $appDataConfigDir)) {
            New-Item -ItemType Directory -Path $appDataConfigDir -Force | Out-Null
            Write-Info "Created Windows roaming config directory: $appDataConfigDir"
        }
    }

    if ($env:LOCALAPPDATA) {
        $localAppDataConfigDir = Join-Path $env:LOCALAPPDATA "code-assistant-manager"
        if (-not (Test-Path $localAppDataConfigDir)) {
            New-Item -ItemType Directory -Path $localAppDataConfigDir -Force | Out-Null
            Write-Info "Created Windows local config directory: $localAppDataConfigDir"
        }
    }

    # Find config files from local dir or installed package
    if (Test-Path "code_assistant_manager") {
        $pkgDir = "code_assistant_manager"
    } else {
        # Try to find from installed package
        try {
            $pkgDir = python -c "import code_assistant_manager, os; print(os.path.dirname(code_assistant_manager.__file__))" 2>$null
        }
        catch {
            $pkgDir = $null
        }
    }

    # Copy config.yaml
    if ($pkgDir -and (Test-Path (Join-Path $pkgDir "config.yaml"))) {
        $configYaml = Join-Path $configDir "config.yaml"
        if (-not (Test-Path $configYaml)) {
            Copy-Item (Join-Path $pkgDir "config.yaml") $configYaml
            Write-Success "Created config.yaml (multi-source repo configuration)"
            Write-Info "  You can edit $configYaml to customize sources"
        } else {
            Write-Info "config.yaml already exists, skipping"
        }
    }

    if ($pkgDir -and (Test-Path (Join-Path $pkgDir "providers.json"))) {
        Copy-Item (Join-Path $pkgDir "providers.json") (Join-Path $configDir "providers.json")
        Write-Success "Created providers.json"
    }

    # Initialize skill_repos.json with built-in repos
    if ($pkgDir -and (Test-Path (Join-Path $pkgDir "skill_repos.json"))) {
        $skillRepos = Join-Path $configDir "skill_repos.json"
        if (-not (Test-Path $skillRepos)) {
            Copy-Item (Join-Path $pkgDir "skill_repos.json") $skillRepos
            Write-Success "Created skill_repos.json with default repositories"
        } else {
            Write-Info "skill_repos.json already exists, skipping"
        }
    }

    # Create .env file if it doesn't exist
    $envFile = Join-Path $env:USERPROFILE ".env"
    if (-not (Test-Path $envFile)) {
        @"
# Add your API keys here
# GITHUB_TOKEN=ghu_your_github_token_here
# API_KEY_CLAUDE=sk-ant-your_claude_key_here
# API_KEY_OPENAI=sk-your_openai_key_here
"@ | Out-File -FilePath $envFile -Encoding UTF8
        # Hide the file
        $file = Get-Item $envFile
        $file.Attributes = $file.Attributes -bor [System.IO.FileAttributes]::Hidden
        Write-Success "Created .env file"
    }
}

function Test-Installation {
    Write-Header "Verifying installation"

    # Check if Python Scripts directory is in PATH
    try {
        $pythonExe = python -c "import sys; print(sys.executable)" 2>$null
        $pythonDir = Split-Path $pythonExe -Parent
        $scriptsDir = Join-Path $pythonDir "Scripts"

        if ($env:PATH -notlike "*$scriptsDir*") {
            Write-Warning "Python Scripts directory not found in PATH"
            Write-Info "To use cam command, add the following to your PATH:"
            Write-Info "  $scriptsDir"
            Write-Info "You can do this by running: [Environment]::SetEnvironmentVariable('Path', `$env:Path + ';$scriptsDir', 'User')"
            Write-Info "Then restart PowerShell"
        }
    }
    catch {
        Write-Warning "Could not determine Python Scripts directory"
    }

    try {
        $version = code-assistant-manager --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "code-assistant-manager command found"
            Write-Info "Version: $version"
        } else {
            Write-Warning "code-assistant-manager not found in PATH"
            Write-Info "You may need to restart PowerShell or add Python Scripts to PATH"
        }
    }
    catch {
        Write-Warning "code-assistant-manager not found in PATH"
        Write-Info "You may need to restart PowerShell or add Python Scripts to PATH"
    }

    try {
        $camVersion = cam --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "cam command found"
        } else {
            Write-Warning "cam not found in PATH"
            Write-Info "You may need to restart PowerShell or add Python Scripts to PATH"
        }
    }
    catch {
        Write-Warning "cam not found in PATH"
        Write-Info "You may need to restart PowerShell or add Python Scripts to PATH"
    }
}

function Uninstall-Package {
    Write-Header "Uninstalling code-assistant-manager"
    $installed = python -m pip show code-assistant-manager 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "code-assistant-manager is not installed in this environment"
        return
    }
    python -m pip uninstall -y code-assistant-manager
    Write-Success "Uninstalled code-assistant-manager"
}

function Clear-Config {
    Write-Header "Purging user configuration"
    $configDir = Join-Path $env:USERPROFILE ".config\code-assistant-manager"
    if (Test-Path $configDir) {
        Remove-Item -Recurse -Force $configDir
        Write-Success "Removed $configDir"
    } else {
        Write-Warning "No user config directory found"
    }

    # Remove Windows-specific config directories
    if ($env:APPDATA) {
        $appDataConfigDir = Join-Path $env:APPDATA "code-assistant-manager"
        if (Test-Path $appDataConfigDir) {
            Remove-Item -Recurse -Force $appDataConfigDir
            Write-Success "Removed $appDataConfigDir"
        }
    }

    if ($env:LOCALAPPDATA) {
        $localAppDataConfigDir = Join-Path $env:LOCALAPPDATA "code-assistant-manager"
        if (Test-Path $localAppDataConfigDir) {
            Remove-Item -Recurse -Force $localAppDataConfigDir
            Write-Success "Removed $localAppDataConfigDir"
        }
    }

    $envFile = Join-Path $env:USERPROFILE ".env"
    if (Test-Path $envFile) {
        Remove-Item -Force $envFile
        Write-Success "Removed ~/.env"
    } else {
        Write-Warning "No ~/.env file found"
    }
}

function Show-Usage {
    Write-Host "Code Assistant Manager PowerShell Installer"
    Write-Host ""
    Write-Host "Usage: .\install.ps1 [-Method] <method> [-Help]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "    -Method    Installation method (pypi, source, uninstall, uninstall-purge, verify)"
    Write-Host "    -Help      Show this help message"
    Write-Host ""
    Write-Host "Methods:"
    Write-Host "    pypi      Install from PyPI (default)"
    Write-Host "    source    Install from GitHub source"
    Write-Host "    uninstall  Uninstall package from current Python environment"
    Write-Host "    uninstall-purge  Uninstall package and remove user config"
    Write-Host "    verify    Only verify current installation"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "    .\install.ps1              # Install from PyPI"
    Write-Host "    .\install.ps1 -Method source  # Install from source"
    Write-Host "    .\install.ps1 -Method verify  # Check current installation"
    Write-Host ""
}

# Main logic
Write-Header "Code Assistant Manager PowerShell Installer"

if ($Help) {
    Show-Usage
    exit 0
}

switch ($Method) {
    "pypi" {
        Test-Python
        Test-Pip
        Install-PyPI
        Setup-Config
        Test-Installation
    }
    "source" {
        Test-Python
        Test-Pip
        Install-Source
        Setup-Config
        Test-Installation
    }
    "verify" {
        Test-Python
        Test-Pip
        Test-Installation
    }
    "uninstall" {
        Test-Python
        Test-Pip
        Uninstall-Package
    }
    "uninstall-purge" {
        Test-Python
        Test-Pip
        Uninstall-Package
        Clear-Config
    }
    default {
        Write-Error "Unknown method: $Method"
        Show-Usage
        exit 1
    }
}

if ($Method -ne "verify") {
    Write-Success "Installation completed!"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "1. Add API keys to $env:USERPROFILE\.env"
    Write-Host "2. Run 'code-assistant-manager doctor' to verify setup"
    Write-Host "3. Try 'code-assistant-manager --help' to see commands"
    Write-Host ""
    Write-Info "For detailed documentation, see:"
    Write-Host "  INSTALL.md - Installation guide"
    Write-Host "  README.md  - Project overview"
}