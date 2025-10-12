# Prompt and Skill Management

Code Assistant Manager includes built-in support for managing **prompts** and **skills** for AI assistants. These features are inspired by the [cc-switch](https://github.com/farion1231/cc-switch) project and provide a unified way to organize and manage your AI assistant configurations.

## Key Features

- **Download skills from GitHub repositories** and install them to `~/.claude/skills/`, `~/.codex/skills/`, or `~/.gemini/skills/`
- **Sync prompts** to the actual tool config files: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`
- **Multi-app support**: Claude, Codex (OpenAI), and Gemini
- **Repository-based skill discovery**: Automatically fetch available skills from configured GitHub repositories

## Prompts

Prompts are reusable text templates that you can apply to any AI assistant. They help you maintain consistent system instructions and context across different tools.

### Quick Start

```bash
# Import the current user-level live prompt from Claude
cam prompt import-live --app claude

# Import the current project-level prompt from the working directory
cam prompt import-live --app claude --level project --project-dir $(pwd)

# Import every live prompt (all apps + levels)
cam prompt import-live --app all --level all --project-dir $(pwd)

# Show the project-level prompt file content
cam prompt show-live --app claude --level project --project-dir $(pwd)

# List all prompts
cam prompt list

# Create a new prompt
cam prompt create my-prompt --name "My Expert Coder" --file my-prompt.md

# Activate a prompt (writes to CLAUDE.md, AGENTS.md, or GEMINI.md)
cam prompt activate my-prompt --app claude

# Show what's currently in the user-level live file
cam prompt show-live --app claude
```

### Prompt File Locations

When you activate a prompt, it's synced to the corresponding app's prompt file:

| App    | File Path                    |
|--------|------------------------------|
| Claude | `~/.claude/CLAUDE.md`        |
| Codex  | `~/.codex/AGENTS.md`         |
| Gemini | `~/.gemini/GEMINI.md`        |

### Managing Prompts

#### List all prompts
```bash
cam prompt list
cam prompt ls       # shorthand
cam p list          # alias
```

#### View a specific prompt
```bash
cam prompt view <prompt-id>
```

#### Create a new prompt
```bash
# Interactive mode (prompts for content)
cam prompt create my-prompt --name "My Prompt" --description "My description"

# From a file
cam prompt create my-prompt --name "My Prompt" --file path/to/prompt.txt
```

#### Update a prompt
```bash
cam prompt update <prompt-id> --name "New Name" --description "New description"
cam prompt update <prompt-id> --file path/to/new-content.txt
```

#### Delete a prompt
```bash
cam prompt delete <prompt-id>
cam prompt delete <prompt-id> --force      # Skip confirmation
```

#### Activate/Deactivate prompts (syncs to app files)
```bash
# Activate a prompt and sync it to Claude's CLAUDE.md (user scope)
cam prompt activate my-prompt --app claude

# Activate for Codex (syncs to AGENTS.md)
cam prompt activate my-prompt --app codex

# Activate for Gemini (syncs to GEMINI.md)
cam prompt activate my-prompt --app gemini

# Activate at the project scope (writes ./CLAUDE.md, ./AGENTS.md, or ./GEMINI.md)
cam prompt activate my-prompt --app claude --level project --project-dir $(pwd)

# Deactivate a prompt
cam prompt deactivate my-prompt
```

#### Sync all active prompts
```bash
cam prompt sync
```

#### Import from live file
```bash
# Import current CLAUDE.md as a new prompt
cam prompt import-live --app claude --name "Imported Prompt"

# Import the prompt stored in the current project's CLAUDE.md
cam prompt import-live --app claude --level project --project-dir $(pwd) --name "Project Prompt"

# Import all user/project prompts for every app
cam prompt import-live --app all --level all --project-dir $(pwd)

# Show current user-level live content
cam prompt show-live --app claude

# Show the project-level prompt content
cam prompt show-live --app claude --level project --project-dir $(pwd)

# Show every prompt file across all apps and levels
cam prompt show-live --app all --level all --project-dir $(pwd)
```

#### Import/Export prompts
```bash
# Export to JSON file
cam prompt export --file ~/my-prompts.json

# Import from JSON file
cam prompt import --file ~/my-prompts.json
```

## Skills

Skills are reusable components that extend the functionality of AI assistants. They can be downloaded from GitHub repositories and installed to the app's skills directory.

### Quick Start

```bash
# Fetch skills from configured repositories
cam skill fetch

# List all available skills
cam skill list

# Install a skill to Claude
cam skill install "owner/repo:skill-name" --app claude

# Uninstall a skill
cam skill uninstall "owner/repo:skill-name" --app claude
```

### Skill Install Locations

When you install a skill, it's copied to the corresponding app's skills directory:

| App    | Directory               |
|--------|-------------------------|
| Claude | `~/.claude/skills/`     |
| Codex  | `~/.codex/skills/`      |
| Gemini | `~/.gemini/skills/`     |

### Default Skill Repositories

The following repositories are pre-configured:
- `anthropics/skills` - Official Anthropic skills
- `ComposioHQ/awesome-claude-skills` - Community curated skills

### Managing Skills

#### Fetch skills from repositories
```bash
cam skill fetch
```

This downloads skill metadata from all enabled repositories and updates your local skill database.

#### List all skills
```bash
cam skill list
cam skill ls              # shorthand
cam s list               # alias

# List with specific app type (affects installed status)
cam skill list --app claude
cam skill list --app codex
cam skill list --app gemini
```

#### View a specific skill
```bash
cam skill view <skill-key>
```

#### Install a skill
```bash
# Install to Claude's skills directory
cam skill install "ComposioHQ/awesome-claude-skills:mcp-builder" --app claude

# Install to Codex
cam skill install "ComposioHQ/awesome-claude-skills:skill-creator" --app codex
```

#### Uninstall a skill
```bash
cam skill uninstall "ComposioHQ/awesome-claude-skills:mcp-builder" --app claude
```

### Managing Skill Repositories

#### List configured repositories
```bash
cam skill repos
```

#### Add a new repository
```bash
cam skill add-repo --owner github-user --name skills-repo --branch main

# With skills in a subdirectory
cam skill add-repo --owner github-user --name skills-repo --branch main --skills-path skills/
```

#### Remove a repository
```bash
cam skill remove-repo --owner github-user --name skills-repo
cam skill remove-repo --owner github-user --name skills-repo --force
```

### Skill Structure

Skills are expected to contain a `SKILL.md` file with YAML front matter:

```markdown
---
name: My Skill
description: What this skill does
---

# My Skill

Detailed skill documentation and instructions...
```

### Import/Export skills
```bash
# Export to JSON file
cam skill export --file ~/my-skills.json

# Import from JSON file
cam skill import --file ~/my-skills.json
```

## Use Cases

### Switch Between Different Prompts for Different Tasks

```bash
# Create specialized prompts
cam prompt create code-review --name "Code Reviewer" --file code-review.md
cam prompt create testing --name "Test Writer" --file testing.md
cam prompt create docs --name "Documentation Writer" --file docs.md

# Switch to code review mode
cam prompt activate code-review --app claude

# Switch to testing mode
cam prompt activate testing --app claude
```

### Install Multiple Skills for a Project

```bash
# Fetch available skills
cam skill fetch

# Install useful skills for development
cam skill install "ComposioHQ/awesome-claude-skills:mcp-builder" --app claude
cam skill install "ComposioHQ/awesome-claude-skills:changelog-generator" --app claude
cam skill install "ComposioHQ/awesome-claude-skills:webapp-testing" --app claude
```

### Sync Prompts Across Multiple AI Assistants

```bash
# Create a shared coding prompt
cam prompt create shared-coder --name "Expert Coder" --file expert-coder.md

# Activate for all assistants
cam prompt activate shared-coder --app claude
cam prompt activate shared-coder --app codex
cam prompt activate shared-coder --app gemini
```

### Backup and Restore Configuration

```bash
# Backup your configuration
cam prompt export --file ~/backups/prompts-backup.json
cam skill export --file ~/backups/skills-backup.json

# Restore on another machine
cam prompt import --file ~/backups/prompts-backup.json
cam skill import --file ~/backups/skills-backup.json
cam prompt sync
```

## GitHub Copilot CLI Custom Instructions Support

The prompt management system now integrates with [GitHub Copilot CLI custom instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions?tool=copilotcli).

This feature allows you to manage Copilot instructions as prompts and sync them to the appropriate repository configuration files.

### About Copilot Instructions

GitHub Copilot CLI supports repository-specific custom instructions that guide Copilot's behavior:

- **Repository-wide instructions** (`.github/copilot-instructions.md`): Apply to all requests in the repository
- **Path-specific instructions** (`.github/instructions/NAME.instructions.md`): Apply to specific file patterns with glob syntax

For more details, see [GitHub Copilot custom instructions documentation](https://docs.github.com/en/copilot/concepts/prompting/response-customization).

### Quick Start with Copilot Instructions

```bash
# Create a prompt for Copilot instructions
cam prompt create copilot-guidelines --name "Copilot Guidelines" --file guidelines.md

# Sync to repository-wide instructions
cam prompt copilot-sync copilot-guidelines --type repo-wide

# Sync to path-specific instructions
cam prompt copilot-sync copilot-guidelines --type path-specific --apply-to "src/**/*.ts"

# Show current Copilot instructions
cam prompt copilot-show --type repo-wide

# Import existing Copilot instructions as a prompt
cam prompt copilot-import --name "Imported Copilot Guidelines"
```

### Managing Copilot Instructions

#### Create and sync repository-wide instructions

```bash
# 1. Create a prompt
cat > my-guidelines.md << 'EOF'
# Code Guidelines
- Write clear, maintainable code
- Always test before committing
- Follow the existing code style
EOF

cam prompt create my-copilot-guidelines --name "My Copilot Guidelines" --file my-guidelines.md

# 2. Sync to .github/copilot-instructions.md
cam prompt copilot-sync my-copilot-guidelines --type repo-wide

# 3. Verify it was created
cam prompt copilot-show --type repo-wide
```

#### Create and sync path-specific instructions

Path-specific instructions use glob patterns to target specific files:

```bash
# 1. Create a prompt for TypeScript files
cat > ts-guidelines.md << 'EOF'
# TypeScript Guidelines
- Use strict mode
- Prefer interfaces over types
- Always add type annotations
EOF

cam prompt create ts-copilot --name "TypeScript Copilot Guidelines" --file ts-guidelines.md

# 2. Sync to path-specific instructions with glob pattern
cam prompt copilot-sync ts-copilot \
  --type path-specific \
  --apply-to "src/**/*.ts,src/**/*.tsx"

# 3. Optionally exclude certain agents
cam prompt copilot-sync ts-copilot \
  --type path-specific \
  --apply-to "src/**/*.ts" \
  --exclude-agent "code-review"
```

The file is created at `.github/instructions/ts-copilot.instructions.md` with frontmatter:

```markdown
---
applyTo: "src/**/*.ts,src/**/*.tsx"
---
# TypeScript Guidelines
...
```

#### Import existing Copilot instructions

```bash
# If you have .github/copilot-instructions.md in your repository
# you can import it as a managed prompt:
cam prompt copilot-import --name "Project Copilot Guidelines"

# List to see the imported prompt
cam prompt list
```

#### Exclude agents from instructions

When syncing path-specific instructions, you can exclude specific agents:

```bash
# Only use for coding-agent, not code-review
cam prompt copilot-sync my-prompt \
  --type path-specific \
  --apply-to "docs/**/*.md" \
  --exclude-agent "code-review"
```

Valid values for `--exclude-agent`:
- `coding-agent` - Exclude Copilot coding agent
- `code-review` - Exclude Copilot code review

### File Locations

When you sync Copilot instructions, they're saved to:

| Type | File Location |
|------|---|
| Repository-wide | `.github/copilot-instructions.md` |
| Path-specific | `.github/instructions/{prompt-id}.instructions.md` |

### Glob Pattern Examples

Path-specific instructions support standard glob syntax:

| Pattern | Matches |
|---------|---------|
| `**` or `**/*` | All files in all directories |
| `*.py` | All `.py` files in the current directory |
| `**/*.py` | All `.py` files recursively |
| `src/**/*.py` | All `.py` files in `src/` recursively |
| `**/*.ts,**/*.tsx` | TypeScript files (comma-separated patterns) |
| `**/subdir/**/*.py` | `.py` files in any `subdir` at any depth |
| `app/models/**/*.rb` | Ruby files in `app/models/` recursively |

## Configuration Directory

All prompt and skill data is stored in:
```
~/.config/code-assistant-manager/
├── prompts.json           # Stored prompts
├── skills.json            # Skill metadata
└── skill_repos.json       # Repository configuration
```

You can backup this directory to preserve your configurations:
```bash
cp -r ~/.config/code-assistant-manager ~/code-assistant-manager-backup
```

## Troubleshooting

### Skills not showing up after fetch
Make sure the repository has valid skills with `SKILL.md` files. Try running:
```bash
cam skill fetch
cam skill list
```

### Prompt not syncing
Check that the prompt is activated, not just enabled:
```bash
cam prompt activate my-prompt --app claude
```

### Repository download fails
Some repositories use `master` instead of `main`. The tool tries both automatically, but you can specify the branch explicitly:
```bash
cam skill add-repo --owner user --name repo --branch master
```
