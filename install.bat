@echo off
REM Code Assistant Manager Windows Installation Script
REM This script provides automated installation for Windows users

setlocal enabledelayedexpansion

REM Colors for output (Windows CMD)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

set "print_info_prefix=%BLUE%ℹ%NC%"
set "print_success_prefix=%GREEN%✓%NC%"
set "print_warning_prefix=%YELLOW%⚠%NC%"
set "print_error_prefix=%RED%✗%NC%"

:print_info
echo %print_info_prefix% %~1
goto :eof

:print_success
echo %print_success_prefix% %~1
goto :eof

:print_warning
echo %print_warning_prefix% %~1
goto :eof

:print_error
echo %print_error_prefix% %~1
goto :eof

:print_header
echo %BLUE%=== %~1 ===%NC%
goto :eof

REM Check Python version
:check_python
call :print_info "Checking Python version..."
python --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Python is not installed"
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
call :print_info "Python version: !PYTHON_VERSION!"

REM Check if Python version is 3.8+
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 (
    call :print_error "Python 3.8+ required"
    exit /b 1
)
call :print_success "Python version is compatible"
goto :eof

REM Check pip
:check_pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
    call :print_error "pip is not available"
    exit /b 1
)
call :print_success "pip is available"
goto :eof

REM Install from PyPI
:install_pypi
call :print_header "Installing from PyPI"
call :print_info "Installing code-assistant-manager..."

REM Check for local wheel
if exist "dist\*.whl" (
    for %%f in (dist\*.whl) do (
        set "WHEEL=%%f"
        goto :found_wheel
    )
)
goto :no_wheel

:found_wheel
call :print_info "Found local wheel: !WHEEL! -- installing (force reinstall, no deps)"
python -m pip install --force-reinstall --no-deps "!WHEEL!" >nul 2>&1
if errorlevel 1 (
    call :print_warning "Failed to install local wheel"
    goto :pypi_fallback
)
call :print_info "Installing runtime dependencies from requirements.txt via PyPI"
python -m pip install --index-url https://pypi.org/simple -r requirements.txt >nul 2>&1
if errorlevel 1 (
    call :print_warning "Failed to install dependencies from PyPI"
    goto :pypi_fallback
)
call :print_success "Installed from local wheel and installed dependencies"
goto :setup_config

:no_wheel
REM Try to build and install local wheel
call :build_and_install_local
if errorlevel 1 (
    goto :pypi_fallback
)
goto :setup_config

:pypi_fallback
python -m pip install --index-url https://pypi.org/simple code-assistant-manager >nul 2>&1
if errorlevel 1 (
    call :print_warning "PyPI install failed; will attempt source install"
    goto :install_source
)
call :print_success "Installed from PyPI"
goto :setup_config

REM Build a wheel locally and install it
:build_and_install_local
call :print_header "Building local wheel"
call :print_info "Ensuring build tools are available..."
python -m pip install --upgrade pip setuptools wheel build >nul 2>&1
if errorlevel 1 (
    call :print_warning "Failed to install build tools"
    exit /b 1
)

call :print_info "Cleaning previous build artifacts..."
if exist "build" rmdir /s /q "build" >nul 2>&1
if exist "dist" rmdir /s /q "dist" >nul 2>&1
for /d %%i in (*.egg-info) do rmdir /s /q "%%i" >nul 2>&1

call :print_info "Running build..."
python -m build >nul 2>&1
if errorlevel 1 (
    call :print_warning "Local build failed"
    exit /b 1
)

if exist "dist\*.whl" (
    for %%f in (dist\*.whl) do (
        set "WHEEL=%%f"
        goto :install_built_wheel
    )
) else (
    call :print_warning "Build completed but no wheel found in dist/"
    exit /b 1
)

:install_built_wheel
call :print_info "Built wheel: !WHEEL! -- installing (no deps)"
python -m pip install --force-reinstall --no-deps "!WHEEL!" >nul 2>&1
if errorlevel 1 (
    call :print_warning "Failed to install built wheel"
    exit /b 1
)
call :print_info "Installing runtime dependencies from requirements.txt via PyPI"
python -m pip install --index-url https://pypi.org/simple -r requirements.txt >nul 2>&1
if errorlevel 1 (
    call :print_warning "Failed to install dependencies from PyPI after build"
    exit /b 1
)
call :print_success "Installed from built wheel and installed dependencies"
exit /b 0

REM Install from source
:install_source
call :print_header "Installing from source"
call :print_info "Cloning repository..."

REM Check if git is available
git --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Git is not available for source installation"
    exit /b 1
)

set "TEMP_DIR=%TEMP%\cam-install-%RANDOM%"
git clone https://github.com/Chat2AnyLLM/code-assistant-manager.git "%TEMP_DIR%" >nul 2>&1
if errorlevel 1 (
    call :print_error "Failed to clone repository"
    exit /b 1
)

cd /d "%TEMP_DIR%"
call :print_info "Installing in development mode..."
python -m pip install -e . >nul 2>&1
if errorlevel 1 (
    call :print_error "Failed to install from source"
    cd /d "%~dp0"
    rmdir /s /q "%TEMP_DIR%" >nul 2>&1
    exit /b 1
)
call :print_success "Installed from source"
cd /d "%~dp0"
rmdir /s /q "%TEMP_DIR%" >nul 2>&1
goto :setup_config

REM Setup configuration
:setup_config
call :print_header "Setting up configuration"

set "CONFIG_DIR=%USERPROFILE%\.config\code-assistant-manager"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%" >nul 2>&1

REM Create Windows-specific config directories
if defined APPDATA (
    set "APPDATA_CONFIG_DIR=%APPDATA%\code-assistant-manager"
    if not exist "%APPDATA_CONFIG_DIR%" mkdir "%APPDATA_CONFIG_DIR%" >nul 2>&1
    call :print_info "Created Windows roaming config directory: %APPDATA_CONFIG_DIR%"
)

if defined LOCALAPPDATA (
    set "LOCALAPPDATA_CONFIG_DIR=%LOCALAPPDATA%\code-assistant-manager"
    if not exist "%LOCALAPPDATA_CONFIG_DIR%" mkdir "%LOCALAPPDATA_CONFIG_DIR%" >nul 2>&1
    call :print_info "Created Windows local config directory: %LOCALAPPDATA_CONFIG_DIR%"
)

REM Find config files from local dir or installed package
if exist "code_assistant_manager" (
    set "PKG_DIR=code_assistant_manager"
) else (
    REM Try to find from installed package
    for /f "delims=" %%i in ('python -c "import code_assistant_manager, os; print(os.path.dirname(code_assistant_manager.__file__))" 2^>nul') do set "PKG_DIR=%%i"
)

REM Copy config.yaml
if defined PKG_DIR (
    if exist "%PKG_DIR%\config.yaml" (
        if not exist "%CONFIG_DIR%\config.yaml" (
            copy "%PKG_DIR%\config.yaml" "%CONFIG_DIR%\config.yaml" >nul 2>&1
            call :print_success "Created config.yaml (multi-source repo configuration)"
            call :print_info "  You can edit %CONFIG_DIR%\config.yaml to customize sources"
        ) else (
            call :print_info "config.yaml already exists, skipping"
        )
    )
)

if defined PKG_DIR (
    if exist "%PKG_DIR%\providers.json" (
        copy "%PKG_DIR%\providers.json" "%CONFIG_DIR%\providers.json" >nul 2>&1
        call :print_success "Created providers.json"
    )
)

REM Initialize skill_repos.json with built-in repos
if defined PKG_DIR (
    if exist "%PKG_DIR%\skill_repos.json" (
        if not exist "%CONFIG_DIR%\skill_repos.json" (
            copy "%PKG_DIR%\skill_repos.json" "%CONFIG_DIR%\skill_repos.json" >nul 2>&1
            call :print_success "Created skill_repos.json with default repositories"
        ) else (
            call :print_info "skill_repos.json already exists, skipping"
        )
    )
)

REM Create .env file if it doesn't exist
if not exist "%USERPROFILE%\.env" (
    echo # Add your API keys here > "%USERPROFILE%\.env"
    echo # GITHUB_TOKEN=ghu_your_github_token_here >> "%USERPROFILE%\.env"
    echo # API_KEY_CLAUDE=sk-ant-your_claude_key_here >> "%USERPROFILE%\.env"
    echo # API_KEY_OPENAI=sk-your_openai_key_here >> "%USERPROFILE%\.env"
    REM Set proper permissions (hide file)
    attrib +h "%USERPROFILE%\.env" >nul 2>&1
    call :print_success "Created .env file"
)
goto :verify_install

REM Verify installation
:verify_install
call :print_header "Verifying installation"

REM Check if Python Scripts directory is in PATH
python -c "import sys; print(sys.executable)" > temp_python_path.txt 2>nul
set /p PYTHON_EXE=<temp_python_path.txt
del temp_python_path.txt >nul 2>&1
for %%i in ("%PYTHON_EXE%") do set "PYTHON_DIR=%%~dpi"
set "SCRIPTS_DIR=%PYTHON_DIR%Scripts"

echo %PATH% | findstr /C:"%SCRIPTS_DIR%" >nul 2>&1
if errorlevel 1 (
    call :print_warning "Python Scripts directory not found in PATH"
    call :print_info "To use cam command, add the following to your PATH:"
    call :print_info "  %SCRIPTS_DIR%"
    call :print_info "You can do this by running: setx PATH \"%%PATH%%;%SCRIPTS_DIR%\""
    call :print_info "Then restart your command prompt"
)

code-assistant-manager --version >nul 2>&1
if errorlevel 1 (
    call :print_warning "code-assistant-manager not found in PATH"
    call :print_info "You may need to restart your command prompt or add Python Scripts to PATH"
) else (
    call :print_success "code-assistant-manager command found"
    for /f "delims=" %%i in ('code-assistant-manager --version 2^>nul') do call :print_info "Version: %%i"
)

cam --version >nul 2>&1
if errorlevel 1 (
    call :print_warning "cam not found in PATH"
    call :print_info "You may need to restart your command prompt or add Python Scripts to PATH"
) else (
    call :print_success "cam command found"
)
goto :main_end

REM Uninstall the package
:uninstall_package
call :print_header "Uninstalling code-assistant-manager"
python -m pip show code-assistant-manager >nul 2>&1
if errorlevel 1 (
    call :print_warning "code-assistant-manager is not installed in this environment"
    goto :eof
)
python -m pip uninstall -y code-assistant-manager >nul 2>&1
call :print_success "Uninstalled code-assistant-manager"
goto :eof

REM Purge user configuration
:purge_config
call :print_header "Purging user configuration"
if exist "%USERPROFILE%\.config\code-assistant-manager" (
    rmdir /s /q "%USERPROFILE%\.config\code-assistant-manager" >nul 2>&1
    call :print_success "Removed %USERPROFILE%\.config\code-assistant-manager"
) else (
    call :print_warning "No user config directory found"
)

if defined APPDATA (
    if exist "%APPDATA%\code-assistant-manager" (
        rmdir /s /q "%APPDATA%\code-assistant-manager" >nul 2>&1
        call :print_success "Removed %APPDATA%\code-assistant-manager"
    )
)

if defined LOCALAPPDATA (
    if exist "%LOCALAPPDATA%\code-assistant-manager" (
        rmdir /s /q "%LOCALAPPDATA%\code-assistant-manager" >nul 2>&1
        call :print_success "Removed %LOCALAPPDATA%\code-assistant-manager"
    )
)

if exist "%USERPROFILE%\.env" (
    del /f /q "%USERPROFILE%\.env" >nul 2>&1
    call :print_success "Removed %USERPROFILE%\.env"
) else (
    call :print_warning "No ~/.env file found"
)
goto :eof

REM Show usage
:show_usage
echo Code Assistant Manager Windows Installer
echo.
echo Usage: %0 [METHOD]
echo.
echo Methods:
echo     pypi      Install from PyPI ^(default^)
echo     source    Install from GitHub source
echo     uninstall  Uninstall package from current Python environment
echo     uninstall-purge  Uninstall package and remove user config
echo     verify    Only verify current installation
echo.
echo Examples:
echo     %0              # Install from PyPI
echo     %0 source       # Install from source
echo     %0 verify       # Check current installation
echo.
goto :eof

REM Main logic
:main
call :print_header "Code Assistant Manager Windows Installer"

if "%1"=="" (
    set "METHOD=pypi"
) else (
    set "METHOD=%1"
)

if "%METHOD%"=="pypi" (
    call :check_python
    call :check_pip
    call :install_pypi
    call :setup_config
    call :verify_install
) else if "%METHOD%"=="source" (
    call :check_python
    call :check_pip
    call :install_source
    call :setup_config
    call :verify_install
) else if "%METHOD%"=="verify" (
    call :check_python
    call :check_pip
    call :verify_install
) else if "%METHOD%"=="uninstall" (
    call :check_python
    call :check_pip
    call :uninstall_package
) else if "%METHOD%"=="uninstall-purge" (
    call :check_python
    call :check_pip
    call :uninstall_package
    call :purge_config
) else if "%METHOD%"=="help" (
    call :show_usage
    goto :main_end
) else if "%METHOD%"=="-h" (
    call :show_usage
    goto :main_end
) else if "%METHOD%"=="--help" (
    call :show_usage
    goto :main_end
) else (
    call :print_error "Unknown method: %METHOD%"
    call :show_usage
    exit /b 1
)

if not "%METHOD%"=="verify" (
    call :print_success "Installation completed^!"
    echo.
    call :print_info "Next steps:"
    echo 1. Add API keys to %USERPROFILE%\.env
    echo 2. Run 'code-assistant-manager doctor' to verify setup
    echo 3. Try 'code-assistant-manager --help' to see commands
    echo.
    call :print_info "For detailed documentation, see:"
    echo   INSTALL.md - Installation guide
    echo   README.md  - Project overview
)

:main_end
goto :eof

call :main %*