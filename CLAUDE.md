# CLAUDE.md — Claude Code Assistant Instructions

This file documents repository-level expectations and instructions intended to guide contributors and AI-assisted editing tools (like Claude Code) when making changes in this project.

- Ask for approval before any git commit and push
- Always run tests before completing all development of new changes
- Always test the CLI usages for the change related
- Never commit credentials, keys, .env files
- After any changes, run the folling to reinstall the project:
- Always update readme, tests and docs for changes
```
rm -rf dist/*
./install.sh uninstall
./install.sh
cp ~/.config/code-assistant-manager/providers.json.bak ~/.config/code-assistant-manager/providers.json
```