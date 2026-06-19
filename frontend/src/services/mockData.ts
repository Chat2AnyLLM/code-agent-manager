import type { ConfigFile, DoctorCheck, Entity, MCPClient, MCPServer, MCPRegistryItem, MetadataItem, Provider, Tool } from './types'

export const mockTools: Tool[] = [
  { name: 'claude-code', command: 'claude', description: 'Claude Code CLI', enabled: true, installed: true, version: 'mock' },
  { name: 'codex', command: 'codex', description: 'OpenAI Codex CLI', enabled: true, installed: false, version: 'unknown' },
]

export const mockProviders: Provider[] = [
  { name: 'local', endpoint: 'http://localhost:4000/v1', apiKeyEnv: 'LOCAL_API_KEY', supportedClient: 'claude,codex', clients: ['claude', 'codex'], models: ['gpt-4.1', 'claude-opus-4.6'], keepProxyConfig: false, useProxy: false, enabled: true, description: 'Local gateway', maskedApiKey: 'loca************_key' },
]

export const mockMCPClients: MCPClient[] = [
  { name: 'claude', userPath: '~/.claude.json', projectPath: '.claude/settings.json', container: 'mcpServers', format: 'json', supportsUser: true, supportsProject: true },
  { name: 'gemini', userPath: '~/.gemini/settings.json', projectPath: '.gemini/settings.json', container: 'mcpServers', format: 'json', supportsUser: true, supportsProject: true },
]

export const mockMCPServers: MCPServer[] = [
  { name: 'github', client: 'claude', scope: 'user', command: 'npx', args: ['-y', '@modelcontextprotocol/server-github'], type: 'stdio' },
]

export const mockMCPRegistry: MCPRegistryItem[] = [
  { name: 'github', displayName: 'GitHub MCP Server', description: 'Tools for interacting with GitHub repositories, issues, and pull requests.', repoUrl: 'https://github.com/modelcontextprotocol/servers', license: 'MIT', categories: ['Dev Tools'], tags: ['github', 'git'], installType: 'npm', installedClients: ['claude'] },
  { name: 'filesystem', displayName: 'Filesystem MCP Server', description: 'Provides file system access for reading, writing, and searching files.', repoUrl: 'https://github.com/modelcontextprotocol/servers', license: 'MIT', categories: ['Dev Tools'], tags: ['files', 'fs'], installType: 'npm', installedClients: [] },
  { name: 'puppeteer', displayName: 'Puppeteer MCP Server', description: 'Browser automation through Puppeteer for web scraping and interaction.', repoUrl: 'https://github.com/modelcontextprotocol/servers', license: 'MIT', categories: ['Web'], tags: ['browser', 'automation'], installType: 'npm', installedClients: [] },
]

export const mockEntities: Entity[] = [
  { kind: 'skill', name: 'golang-testing', description: 'Go testing guidance', apps: ['claude'], tags: ['go', 'testing'], updatedAt: '2026-06-16T00:00:00Z' },
  { kind: 'agent', name: 'code-reviewer', description: 'Review code changes', apps: ['claude'], tags: ['review'], updatedAt: '2026-06-16T00:00:00Z' },
]

export const mockConfigFiles: ConfigFile[] = [
  { app: 'cam', scope: 'user', path: '~/.config/code-agent-manager/config.yaml', format: 'yaml', exists: true },
  { app: 'claude', scope: 'project', path: '.claude/settings.json', format: 'json', exists: true },
]

export const mockDoctorChecks: DoctorCheck[] = [
  { name: 'Installation Check', issues: 0, messages: [{ level: 'pass', text: 'Code Assistant Manager installed' }] },
  { name: 'Configuration Check', issues: 0, messages: [{ level: 'pass', text: 'providers.json is valid' }] },
]

export const mockMetadataItems: MetadataItem[] = [
  { kind: 'skill', name: 'golang-testing', description: 'Go testing guidance', install_key: 'obra/superpowers:golang-testing', repo_owner: 'obra', repo_name: 'superpowers', repo_branch: 'main', target_apps: 'claude,codex', installed_apps: ['claude'], installed: true },
  { kind: 'agent', name: 'code-reviewer', description: 'Review code changes', install_key: 'iannuttall/claude-agents:code-reviewer', repo_owner: 'iannuttall', repo_name: 'claude-agents', repo_branch: 'main', target_apps: 'claude', installed_apps: [], installed: false },
  { kind: 'prompt', name: 'summarize', description: 'Summarize long text', install_key: 'anthropics/prompts:summarize', repo_owner: 'anthropics', repo_name: 'prompts', repo_branch: 'main', target_apps: 'claude,codex', installed_apps: [], installed: false },
  { kind: 'plugin', name: 'superpowers-marketplace', description: 'Curated Claude Code plugins', install_key: 'obra/superpowers-marketplace:superpowers-marketplace', repo_owner: 'obra', repo_name: 'superpowers-marketplace', repo_branch: 'main', target_apps: 'claude', installed_apps: [], installed: false },
]

export const mockTargets: Record<string, string[]> = {
  skill: ['claude', 'codex', 'copilot', 'cursor', 'gemini'],
  agent: ['claude', 'codex', 'copilot', 'cursor', 'gemini'],
  prompt: ['claude', 'codex', 'copilot', 'gemini'],
  plugin: ['claude', 'codebuddy'],
}
