# Quick Reference: Prompt & Skill Management

## Prompt Commands

### Basic Operations
```bash
# List all prompts
cam prompt list          # or: cam p list

# View a prompt
cam prompt view <id>

# Create a new prompt
cam prompt create <id> --name "Name" --description "Description"

# Update a prompt
cam prompt update <id> --name "New Name"

# Delete a prompt
cam prompt delete <id>
```

### Enable/Disable
```bash
# Enable a prompt
cam prompt enable <id>

# Disable a prompt
cam prompt disable <id>
```

### Import/Export
```bash
# Export all prompts
cam prompt export --file ~/prompts.json

# Import prompts
cam prompt import --file ~/prompts.json
```

## Skill Commands

### Basic Operations
```bash
# List all skills
cam skill list           # or: cam s list

# View a skill
cam skill view <key>

# Create a new skill
cam skill create <key> --name "Name" --description "Desc" --directory "/path"

# Update a skill
cam skill update <key> --name "New Name"

# Delete a skill
cam skill delete <key>
```

### Install/Uninstall
```bash
# Install a skill
cam skill install <key>

# Uninstall a skill
cam skill uninstall <key>
```

### Repository Management
```bash
# List repositories
cam skill repos

# Add a repository
cam skill add-repo --owner "user" --name "repo" --branch "main"

# Remove a repository
cam skill remove-repo --owner "user" --name "repo"
```

### Import/Export
```bash
# Export all skills
cam skill export --file ~/skills.json

# Import skills
cam skill import --file ~/skills.json
```

## Data Storage

Prompts and skills are stored as JSON in:
- `~/.config/code-assistant-manager/prompts.json`
- `~/.config/code-assistant-manager/skills.json`
- `~/.config/code-assistant-manager/skill_repos.json`

Backup or version control these files to preserve your configurations.

## Tips

1. Use aliases for faster command entry:
   - `cam p` for prompts
   - `cam s` for skills

2. Use `--force` flag to skip confirmation prompts:
   - `cam prompt delete <id> --force`
   - `cam skill delete <key> --force`

3. Export before making changes to have a backup:
   - `cam prompt export --file ~/backups/prompts-$(date +%Y%m%d).json`

4. Import/export for sharing with team members or transferring between machines

## Common Workflows

### Organizing Prompts for Different Contexts
```bash
cam prompt create system --name "System" --file system-prompt.txt
cam prompt create coding --name "Coding" --file coding-prompt.txt
cam prompt create reviewing --name "Review" --file review-prompt.txt

# Switch context
cam prompt enable system
cam prompt disable coding
```

### Setting Up Skills
```bash
# Add a skills repository
cam skill add-repo --owner "myorg" --name "skills" --branch "main"

# Create skills in that repo
cam skill create web-dev --name "Web Dev" --directory "/skills/web" \
  --repo-owner "myorg" --repo-name "skills"

# Install the skill
cam skill install web-dev
```

### Backup and Restore
```bash
# Backup
cam prompt export --file ~/backup/prompts.json
cam skill export --file ~/backup/skills.json

# Restore
cam prompt import --file ~/backup/prompts.json
cam skill import --file ~/backup/skills.json
```
