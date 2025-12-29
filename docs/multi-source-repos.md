# Multi-Source Repository Configuration

Code Assistant Manager now supports loading repository configurations from multiple sources, allowing you to use both local custom repos and community-maintained remote repos.

## How It Works

Repository configurations (for skills, agents, and plugins) are loaded from multiple sources in priority order:

1. **Local files** (highest priority) - Your custom repos
   - `~/.config/code-assistant-manager/skill_repos.json`
   - `~/.config/code-assistant-manager/agent_repos.json`
   - `~/.config/code-assistant-manager/plugin_repos.json`

2. **Remote URLs** - Community repos (with caching)
   - `https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/main/skill_repos.json`
   - `https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/main/agent_repos.json`
   - `https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/main/plugin_repos.json`

3. **Bundled defaults** (fallback) - Package defaults
   - Built-in repositories included with the package

## Configuration

The sources are configured in `config.yaml`:

### Default Configuration

The bundled `config.yaml` is located at:
```
code_assistant_manager/config.yaml
```

It defines the default sources for each repository type.

### User Configuration

You can override the configuration by creating:
```
~/.config/code-assistant-manager/config.yaml
```

### Configuration Format

```yaml
repositories:
  # Skill repositories
  skills:
    sources:
      # Local user file (highest priority)
      - type: local
        path: ~/.config/code-assistant-manager/skill_repos.json
      
      # Remote awesome repository configs
      - type: remote
        url: https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/main/skill_repos.json
  
  # Agent repositories
  agents:
    sources:
      - type: local
        path: ~/.config/code-assistant-manager/agent_repos.json
      - type: remote
        url: https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/main/agent_repos.json
  
  # Plugin repositories
  plugins:
    sources:
      - type: local
        path: ~/.config/code-assistant-manager/plugin_repos.json
      - type: remote
        url: https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/main/plugin_repos.json

# Cache settings for remote sources
cache:
  enabled: true
  directory: ~/.cache/code-assistant-manager/repos
  ttl_seconds: 3600  # Cache remote sources for 1 hour
```

## Adding Custom Repositories

### Option 1: Local File (Recommended for personal repos)

Create a local repo file at `~/.config/code-assistant-manager/skill_repos.json`:

```json
{
  "mycompany/my-skills": {
    "owner": "mycompany",
    "name": "my-skills",
    "branch": "main",
    "enabled": true,
    "skillsPath": "skills"
  }
}
```

Local repos have highest priority and will override remote repos with the same key.

### Option 2: Add Remote Source

Edit `~/.config/code-assistant-manager/config.yaml` to add more remote sources:

```yaml
repositories:
  skills:
    sources:
      - type: local
        path: ~/.config/code-assistant-manager/skill_repos.json
      - type: remote
        url: https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/main/skill_repos.json
      # Add your custom remote source
      - type: remote
        url: https://mycompany.com/repos/skill_repos.json
```

## Caching

Remote repositories are cached locally to:
```
~/.cache/code-assistant-manager/repos/
```

Cache files are named based on the repository type and source URL.

### Cache Behavior

- Remote sources are cached for 1 hour by default (configurable via `cache.ttl_seconds`)
- If cache is fresh, no network request is made
- If cache is expired or doesn't exist, repos are fetched from remote URL
- If remote fetch fails, cached data (if any) is used
- If both fail, bundled defaults are used

### Clear Cache

To force refresh from remote sources, delete the cache directory:
```bash
rm -rf ~/.cache/code-assistant-manager/repos/
```

## How Sources are Merged

When multiple sources provide the same repository (matched by key), priority is:

1. Local file wins (always used if present)
2. Remote sources (first source in config.yaml wins)
3. Bundled defaults (used as ultimate fallback)

This allows you to:
- Override community repos with your custom versions
- Add new repos via local files
- Benefit from community updates for non-overridden repos

## Example Use Cases

### Use Case 1: Company-Specific Skills

```yaml
repositories:
  skills:
    sources:
      # Company repos (highest priority)
      - type: local
        path: ~/.config/code-assistant-manager/skill_repos.json
      # Community repos
      - type: remote
        url: https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/main/skill_repos.json
```

Create `~/.config/code-assistant-manager/skill_repos.json`:
```json
{
  "mycompany/internal-skills": {
    "owner": "mycompany",
    "name": "internal-skills",
    "branch": "main",
    "enabled": true
  }
}
```

Now you get both company-specific and community skills!

### Use Case 2: Test New Repositories

```yaml
repositories:
  skills:
    sources:
      - type: local
        path: ~/.config/code-assistant-manager/skill_repos.json
      # Stable community repos
      - type: remote
        url: https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/main/skill_repos.json
      # Experimental repos
      - type: remote
        url: https://raw.githubusercontent.com/Chat2AnyLLM/awesome-repo-configs/dev/skill_repos.json
```

### Use Case 3: Offline Development

Create local copies of all repos in:
- `~/.config/code-assistant-manager/skill_repos.json`
- `~/.config/code-assistant-manager/agent_repos.json`
- `~/.config/code-assistant-manager/plugin_repos.json`

Comment out or remove remote sources from config.yaml. Now everything works offline!

## Benefits

✅ **Community Updates**: Automatically get new repos from community sources
✅ **Custom Overrides**: Add your own repos without modifying community lists
✅ **Offline Support**: Local and bundled fallbacks work without internet
✅ **Flexible**: Configure multiple sources, prioritize as needed
✅ **Cached**: Remote sources are cached to reduce network requests

## Implementation Details

### RepoConfigLoader

The `RepoConfigLoader` class in `code_assistant_manager/repo_loader.py` handles:
- Loading config.yaml
- Fetching from local and remote sources
- Caching remote sources
- Merging repos from multiple sources
- Fallback to bundled defaults

### Managers

The managers (`skills/manager.py`, `agents/manager.py`, `plugins/manager.py`) use `RepoConfigLoader` to get repository configurations at initialization time.

### Backward Compatibility

If config.yaml doesn't exist, the system falls back to bundled defaults, maintaining backward compatibility with existing installations.
