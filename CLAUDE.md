# CLAUDE.md — Claude Code Assistant Instructions

This file documents repository-level expectations and instructions intended to guide contributors and AI-assisted editing tools (like Claude Code) when making changes in this project.

- Ask for approval before any git commit and push
- Always all tests by find all fils with 'find' command and run them all one by one
- Never commit credentials, keys, .env files
- After any changes, run the folling to reinstall the project:
```
rm -rf dist/*
./install.sh uninstall
./install.sh
cp ~/.config/code-assistant-manager/providers.json.bak ~/.config/code-assistant-manager/providers.json
```