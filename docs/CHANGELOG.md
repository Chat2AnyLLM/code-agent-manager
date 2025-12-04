# Changelog

## [Unreleased]

### Added
- **Fancy Name Generation**: ✨ Auto-generate creative prompt names like "Cosmic Coder" or "Quantum Assistant" when adding or importing prompts
- **Enhanced Prompt Update Command**: New `cam prompt update` command with `--file` option to update prompt content, description, name, and default status
- **Improved Prompt Status**: `cam prompt status` now shows file paths alongside app:level information for better visibility
- **Optional Prompt Names**: `cam prompt add` and `cam prompt import` commands now support optional names with automatic fancy name generation

### Changed
- **Prompt CLI Commands**: Updated command structure to be more intuitive:
  - `cam prompt add` - Add prompts (auto-generates names if not provided)
  - `cam prompt update` - Update existing prompts with content from files
  - `cam prompt import` - Import from live app files with fancy names
  - `cam prompt install` - Install configured prompts to app files
  - `cam prompt status` - Enhanced to show file paths

## [1.0.3] - 2024-10-18

### Changed
- **BREAKING**: Removed individual command entry points (e.g., `codex`, `claude`, `droid`) from setup.py to avoid PATH conflicts with native CLI tools
- Users should now run tools using `code-assistant-manager <tool>` or `python -m code_assistant_manager <tool>` instead of standalone commands
- Added `__main__.py` to support running as a Python module: `python -m code_assistant_manager`

### Fixed
- Fixed issue where `codex` command would repeatedly prompt for upgrade due to PATH conflicts
  - The Code-Assistant-Manager wrapper was finding itself when checking if the tool was installed
  - Native CLI tools from npm (e.g., `@openai/codex`, `@anthropic-ai/claude-code`) are now properly detected in PATH
- Removed circular dependency where wrapper scripts would detect themselves

### Migration Guide
If you previously used standalone commands like:
```bash
codex --help
claude "help me code"
```

You should now use:
```bash
code-assistant-manager codex --help
code-assistant-manager claude "help me code"

# Or via Python module:
python -m code_assistant_manager codex --help
python -m code_assistant_manager claude "help me code"
```

### Technical Details
- Removed `claude_main`, `codex_main`, `droid_main`, `qwen_main`, `codebuddy_main`, `copilot_main`, `gemini_main`, `iflow_main`, `qodercli_main`, and `zed_main` entry points from setup.py
- Updated tests to reflect new invocation pattern
- Updated documentation in README.md to show both invocation methods

## [1.0.2] - 2024-10-XX

### Previous releases
See git history for earlier changes.
