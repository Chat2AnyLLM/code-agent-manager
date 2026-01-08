<!-- Sync Impact Report for Constitution v1.0.0
Version change: N/A → 1.0.0
Added sections: Core Principles, Development Workflow, Governance
Removed sections: None
Modified principles: None (initial creation)
Added sections: Core Principles, Development Workflow, Governance
Removed sections: None
Templates requiring updates: ✅ updated .specify/templates/plan-template.md (constitution check section)
Follow-up TODOs: None
-->
# Code Assistant Manager Constitution

## Core Principles

### I. Unified Interface
All AI assistant management MUST occur through a single, consistent CLI interface. The `cam` command serves as the universal entry point for installing, configuring, and operating 17+ supported AI assistants. No direct tool interactions allowed - all operations flow through CAM's standardized protocols.

### II. Security First
Enterprise-grade security is non-negotiable. All configurations use secure file-based storage with environment variable support. MCP client implementations eliminate shell injection vulnerabilities. API keys and credentials are never committed to version control.

### III. Test-Driven Development
Every feature implementation MUST follow TDD principles: tests written first, then code to make tests pass. Comprehensive test suite with 1400+ tests required. All changes trigger automated testing before commits.

### IV. Extensibility Framework
CAM MUST maintain a standardized architecture supporting agents, prompts, skills, and plugins. All extensions use markdown-based configurations with YAML front matter. MCP registry provides 381+ pre-configured servers.

### V. Quality Assurance
Automated quality gates enforce code standards: black formatting, flake8 linting, mypy type checking, and security scanning. Pre-commit hooks prevent non-compliant code. Coverage requirements and complexity monitoring ensure maintainability.

## Development Workflow

### Commit Protocol
- Ask for user approval before any git commit and push
- Run complete test suite using `find` command to locate all test files and execute them sequentially
- Documentation-only changes skip testing
- Never commit credentials, keys, or .env files

### Post-Change Validation
After any code changes, reinstall the project using the standard sequence:
```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
cp ~/.config/code-assistant-manager/providers.json.bak ~/.config/code-assistant-manager/providers.json
```

### Quality Gates
- Code formatting: black with 88-character line length
- Linting: flake8 with bugbear, comprehensions, and simplify rules
- Type checking: mypy with strict configuration
- Security: bandit scanning excluding test directories
- Documentation: interrogate with 50% coverage minimum

## Governance

Constitution supersedes all other practices. Amendments require:
1. Clear rationale documented in commit message
2. Version bump following semantic versioning
3. All dependent templates updated if principles change
4. Test suite passes after changes

All PRs/reviews MUST verify constitution compliance. Complexity increases require explicit justification. Use CLAUDE.md for runtime development guidance.

**Version**: 1.0.0 | **Ratified**: 2026-01-02 | **Last Amended**: 2026-01-02
