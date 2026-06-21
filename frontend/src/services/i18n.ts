import { createContext, createElement, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'

// Internationalization for the desktop UI. Mirrors the theme service: a single
// active language selected at runtime, defaulting to English, persisted across
// launches in localStorage. Strings live in a flat key → translation map per
// language so a missing key falls back to the key itself (visible, not blank).

export type Language = 'en' | 'zh'

const STORAGE_KEY = 'cam.lang'

// Flat dictionaries. Keys are dotted for grouping only; there is no nesting.
// English is the source of truth — every key MUST exist in `en`. Chinese
// entries that are missing fall back to the English string at lookup time.
const en: Record<string, string> = {
  'brand': 'CAM Desktop',
  'lang.toggle': '中文',
  'theme.light': 'Light mode',
  'theme.dark': 'Dark mode',

  // Generic table expand/collapse affordance
  'table.details': 'Details',
  'table.hideDetails': 'Hide details',

  // Providers page
  'providers.apiKey': 'API key',
  'providers.apiKeyPlaceholder': 'sk-… (stored with provider)',
  'providers.apiKeyHint': 'Literal API key stored with the provider and written into agent configs. Takes precedence over the env var.',
  'providers.setApiKey': 'Set API key',
  'providers.setApiKeyEnv': 'Set API key env var',
  'providers.apiKeySave': 'Save key',
  'providers.apiKeySaving': 'Saving…',
  'providers.apiKeySaved': 'Saved.',
  'providers.apiKeyEnv': 'API key env',
  'providers.apiKeyEnvHint': 'Name of the env var holding the key (e.g. OPENAI_API_KEY)',
  'providers.maskedKey': 'API key',
  'providers.clients': 'Clients',
  'providers.description': 'Description',

  // Navigation
  'nav.agents': 'Agents',
  'nav.providers': 'Providers',
  'nav.mcp': 'MCP Servers',
  'nav.instructions': 'Instructions',
  'nav.skills': 'Skills',
  'nav.subagents': 'Subagents',
  'nav.plugins': 'Plugins',
  'nav.config': 'Configuration',
  'nav.diagnostics': 'Diagnostics',
  'nav.settings': 'Settings',

  // Agents (runnable code agents) page
  'agents.title': 'Agents',
  'agents.description': 'Coding agents CAM manages. Run each from your terminal with the command shown after configuring providers, MCP servers, instructions, skills, subagents, and plugins.',
  'agents.detected': 'Detected: {version}',
  'agents.notDetected': 'Not detected on PATH',
  'agents.installed': 'Installed',
  'agents.notInstalled': 'Not installed',
  'agents.install': 'Install',
  'agents.installing': 'Installing…',
  'agents.upgrade': 'Upgrade',
  'agents.upgrading': 'Upgrading…',
  'agents.installDone': 'Installed {name}',
  'agents.upgradeDone': 'Upgraded {name}',
  'agents.lifecycleFailed': '{action} failed: {error}',
  'agents.installedResources': 'Installed resources',
  'agents.provider': 'Provider',
  'agents.model': 'Model',
  'agents.apply': 'Apply',
  'agents.applying': 'Applying…',
  'agents.applied': 'Applied → {path} ({count} keys)',
  'agents.applyFailed': 'Apply failed: {error}',
  'agents.noConfigTarget': 'This agent has no config file to write.',
  'agents.pickProviderFirst': 'Pick a provider and model first.',

  // Library (skills/subagents/plugins) pages
  'library.skills.title': 'Skills',
  'library.skills.description': 'Search, install, and refresh Claude-style skills from the metadata index.',
  'library.agents.title': 'Subagents',
  'library.agents.description': 'Search, install, and refresh custom subagents from the metadata index.',
  'library.plugins.title': 'Plugins',
  'library.plugins.description': 'Search, install, and refresh assistant plugins from the metadata index.',
  'library.searchPlaceholder': 'Search {kind}',
  'library.search': 'Search',
  'library.reset': 'Reset',
  'library.refresh': 'Refresh',
  'library.refreshing': 'Refreshing…',
  'library.installedOnly': 'Installed only',
  'library.empty': 'No {kind} found. Try refreshing the index.',
  'library.noDescription': '(no description)',
  'library.notInstalled': 'not installed',
  'library.installedAgents': 'installed agents',
  'library.installTargets': 'install targets for {name}',
  'library.installTo': 'Install to {target}',
  'library.installToCount': 'Install to {count} agents',
  'library.installing': 'Installing…',
  'library.selectTargets': 'Select agents',
  'library.selectAgentsFor': 'Select agents for {name}',
  'library.expand': 'Details',
  'library.collapse': 'Hide details',
  'library.loadingDetail': 'Loading details…',
  'library.detailFailed': 'Could not load details.',
  'library.manifestPath': 'Source: {path}',
  'library.pagination': 'Page {current} of {total} ({count} total)',
  'library.previous': 'Previous',
  'library.next': 'Next',
  'library.uninstall': 'Uninstall',
  'library.uninstalled': 'Uninstalled {name} from {targets}',
  'library.uninstallFailed': 'Uninstall failed: {error}',
  'library.refreshItem': 'Refresh',
  'library.refreshingItem': 'Refreshing\u2026',
  'library.refreshItemDone': 'Refreshed {name}',
  'library.refreshItemFailed': 'Refresh failed: {error}',
  'library.cachedAt': 'Cached: {time}',

  // MCP Servers page (mirrors the Library layout: discovered registry servers
  // with a per-row install-target dropdown)
  'mcp.title': 'MCP Servers',
  'mcp.description': 'Browse discovered MCP servers and install them to your code agents.',
  'mcp.searchPlaceholder': 'Search MCP servers',
  'mcp.search': 'Search',
  'mcp.reload': 'Reload',
  'mcp.reloading': 'Reloading…',
  'mcp.installedOnly': 'Installed only',
  'mcp.empty': 'No MCP servers found. Try a different search.',
  'mcp.noDescription': '(no description)',
  'mcp.notInstalled': 'not installed',
  'mcp.installedClients': 'installed clients',
  'mcp.installTargets': 'install targets for {name}',
  'mcp.installTo': 'Install to {target}',
  'mcp.installToCount': 'Install to {count} agents',
  'mcp.installing': 'Installing…',
  'mcp.selectTargets': 'Select agents',
  'mcp.selectAgentsFor': 'Select agents for {name}',
  'mcp.installed': 'Installed {name} to {targets}',
  'mcp.installFailed': 'Install failed: {error}',
  'mcp.searchFailed': 'Search failed: {error}',
  'mcp.uninstall': 'Uninstall',
  'mcp.uninstalled': 'Uninstalled {name} from {targets}',
  'mcp.uninstallFailed': 'Uninstall failed: {error}',

  // Instructions page (local CRUD + symlink install)
  'instructions.title': 'Instructions',
  'instructions.description': 'Author local instruction files (CLAUDE.md, AGENTS.md, GEMINI.md, …), save them in CAM, and install them to a coding-agent path via symlink.',
  'instructions.new': '+ New instruction',
  'instructions.searchPlaceholder': 'Search instructions',
  'instructions.empty': 'No instructions yet. Create one to get started.',
  'instructions.colName': 'Name',
  'instructions.colDescription': 'Description',
  'instructions.colInstalled': 'Installed',
  'instructions.colActions': 'Actions',
  'instructions.edit': 'Edit',
  'instructions.delete': 'Delete',
  'instructions.install': 'Install',
  'instructions.notInstalled': 'not installed',
  'instructions.uninstall': 'Uninstall {app} ({level})',
  'instructions.copyBadge': 'copy',
  'instructions.copyTooltip': 'Installed as a copy; re-install to pick up edits.',
  'instructions.copyFallbackBanner': 'Symlinks are unavailable here, so the instruction was copied. Re-install after editing to refresh the copy.',
  'instructions.confirmDelete': 'Delete this instruction and remove all its installs?',
  'instructions.newTitle': 'New instruction',
  'instructions.editTitle': 'Edit instruction',
  'instructions.name': 'Name',
  'instructions.descriptionLabel': 'Description',
  'instructions.content': 'Content',
  'instructions.save': 'Save',
  'instructions.saving': 'Saving…',
  'instructions.cancel': 'Cancel',
  'instructions.nameInvalid': 'Name may contain only letters, numbers, dot, underscore and dash.',
  'instructions.nameTaken': "An instruction named '{name}' already exists.",
  'instructions.installTitle': 'Install {name}',
  'instructions.agent': 'Agent',
  'instructions.agents': 'Agents',
  'instructions.noAgentSelected': 'Select at least one agent.',
  'instructions.noSupportedAgent': 'No selected agent supports the chosen level.',
  'instructions.level': 'Level',
  'instructions.levelUser': 'User',
  'instructions.levelProject': 'Project',
  'instructions.projectDir': 'Project directory',
  'instructions.projectDirRequired': 'Project directory is required for project-level install.',
  'instructions.installButton': 'Install',
  'instructions.installing': 'Installing…',
}

const zh: Record<string, string> = {
  'brand': 'CAM 桌面版',
  'lang.toggle': 'English',
  'theme.light': '浅色模式',
  'theme.dark': '深色模式',

  // Generic table expand/collapse affordance
  'table.details': '详情',
  'table.hideDetails': '隐藏详情',

  // Providers page
  'providers.apiKey': 'API 密钥',
  'providers.apiKeyPlaceholder': 'sk-…（与提供商一起保存）',
  'providers.apiKeyHint': '与提供商一起保存并写入各代理配置的 API 密钥，优先级高于环境变量。',
  'providers.setApiKey': '设置 API 密钥',
  'providers.setApiKeyEnv': '设置 API 密钥环境变量',
  'providers.apiKeySave': '保存密钥',
  'providers.apiKeySaving': '保存中…',
  'providers.apiKeySaved': '已保存。',
  'providers.apiKeyEnv': 'API 密钥环境变量',
  'providers.apiKeyEnvHint': '存放密钥的环境变量名（例如 OPENAI_API_KEY）',
  'providers.maskedKey': 'API 密钥',
  'providers.clients': '客户端',
  'providers.description': '描述',

  // Navigation
  'nav.agents': '智能体',
  'nav.providers': '服务商',
  'nav.mcp': 'MCP 服务器',
  'nav.instructions': '指令',
  'nav.skills': '技能',
  'nav.subagents': '子智能体',
  'nav.plugins': '插件',
  'nav.config': '配置',
  'nav.diagnostics': '诊断',
  'nav.settings': '设置',

  // Agents page
  'agents.title': '智能体',
  'agents.description': 'CAM 管理的编程智能体。配置好服务商、MCP 服务器、指令、技能、子智能体和插件后，在终端使用下方命令运行各智能体。',
  'agents.detected': '已检测：{version}',
  'agents.notDetected': '未在 PATH 中检测到',
  'agents.installed': '已安装',
  'agents.notInstalled': '未安装',
  'agents.install': '安装',
  'agents.installing': '安装中…',
  'agents.upgrade': '升级',
  'agents.upgrading': '升级中…',
  'agents.installDone': '已安装 {name}',
  'agents.upgradeDone': '已升级 {name}',
  'agents.lifecycleFailed': '{action} 失败：{error}',
  'agents.installedResources': '已安装资源',
  'agents.provider': '服务商',
  'agents.model': '模型',
  'agents.apply': '应用',
  'agents.applying': '应用中…',
  'agents.applied': '已应用 → {path}（{count} 项）',
  'agents.applyFailed': '应用失败：{error}',
  'agents.noConfigTarget': '该智能体没有可写入的配置文件。',
  'agents.pickProviderFirst': '请先选择服务商和模型。',

  // Library pages
  'library.skills.title': '技能',
  'library.skills.description': '从元数据索引中搜索、安装并刷新 Claude 风格的技能。',
  'library.agents.title': '子智能体',
  'library.agents.description': '从元数据索引中搜索、安装并刷新自定义子智能体。',
  'library.plugins.title': '插件',
  'library.plugins.description': '从元数据索引中搜索、安装并刷新助手插件。',
  'library.searchPlaceholder': '搜索{kind}',
  'library.search': '搜索',
  'library.reset': '重置',
  'library.refresh': '刷新',
  'library.refreshing': '刷新中…',
  'library.installedOnly': '仅显示已安装',
  'library.empty': '未找到{kind}。请尝试刷新索引。',
  'library.noDescription': '（无描述）',
  'library.notInstalled': '未安装',
  'library.installedAgents': '已安装的智能体',
  'library.installTargets': '{name} 的安装目标',
  'library.installTo': '安装到 {target}',
  'library.installToCount': '安装到 {count} 个智能体',
  'library.installing': '安装中…',
  'library.selectTargets': '选择智能体',
  'library.selectAgentsFor': '为 {name} 选择智能体',
  'library.expand': '详情',
  'library.collapse': '隐藏详情',
  'library.loadingDetail': '正在加载详情…',
  'library.detailFailed': '无法加载详情。',
  'library.manifestPath': '来源：{path}',
  'library.pagination': '第 {current} / {total} 页（共 {count} 项）',
  'library.previous': '上一页',
  'library.next': '下一页',
  'library.uninstall': '卸载',
  'library.uninstalled': '已从 {targets} 卸载 {name}',
  'library.uninstallFailed': '卸载失败：{error}',
  'library.refreshItem': '刷新',
  'library.refreshingItem': '刷新中\u2026',
  'library.refreshItemDone': '已刷新 {name}',
  'library.refreshItemFailed': '刷新失败：{error}',
  'library.cachedAt': '缓存时间：{time}',

  // MCP 服务器页面（沿用 Library 的布局：已发现的注册表服务器 + 每行安装目标下拉框）
  'mcp.title': 'MCP 服务器',
  'mcp.description': '浏览已发现的 MCP 服务器并将其安装到你的编程智能体。',
  'mcp.searchPlaceholder': '搜索 MCP 服务器',
  'mcp.search': '搜索',
  'mcp.reload': '重新加载',
  'mcp.reloading': '加载中…',
  'mcp.installedOnly': '仅显示已安装',
  'mcp.empty': '未找到 MCP 服务器。请尝试其他搜索词。',
  'mcp.noDescription': '（无描述）',
  'mcp.notInstalled': '未安装',
  'mcp.installedClients': '已安装的客户端',
  'mcp.installTargets': '{name} 的安装目标',
  'mcp.installTo': '安装到 {target}',
  'mcp.installToCount': '安装到 {count} 个智能体',
  'mcp.installing': '安装中…',
  'mcp.selectTargets': '选择智能体',
  'mcp.selectAgentsFor': '为 {name} 选择智能体',
  'mcp.installed': '已将 {name} 安装到 {targets}',
  'mcp.installFailed': '安装失败：{error}',
  'mcp.searchFailed': '搜索失败：{error}',
  'mcp.uninstall': '卸载',
  'mcp.uninstalled': '已从 {targets} 卸载 {name}',
  'mcp.uninstallFailed': '卸载失败：{error}',

  // 指令页面（本地增删改查 + 符号链接安装）
  'instructions.title': '指令',
  'instructions.description': '在本地编写指令文件（CLAUDE.md、AGENTS.md、GEMINI.md 等），保存到 CAM，并通过符号链接安装到编程智能体路径。',
  'instructions.new': '+ 新建指令',
  'instructions.searchPlaceholder': '搜索指令',
  'instructions.empty': '暂无指令。新建一个开始使用。',
  'instructions.colName': '名称',
  'instructions.colDescription': '描述',
  'instructions.colInstalled': '已安装',
  'instructions.colActions': '操作',
  'instructions.edit': '编辑',
  'instructions.delete': '删除',
  'instructions.install': '安装',
  'instructions.notInstalled': '未安装',
  'instructions.uninstall': '卸载 {app}（{level}）',
  'instructions.copyBadge': '副本',
  'instructions.copyTooltip': '以副本方式安装；编辑后需重新安装才能生效。',
  'instructions.copyFallbackBanner': '此处无法创建符号链接，已改为复制。编辑后请重新安装以刷新副本。',
  'instructions.confirmDelete': '删除此指令并移除其所有安装？',
  'instructions.newTitle': '新建指令',
  'instructions.editTitle': '编辑指令',
  'instructions.name': '名称',
  'instructions.descriptionLabel': '描述',
  'instructions.content': '内容',
  'instructions.save': '保存',
  'instructions.saving': '保存中…',
  'instructions.cancel': '取消',
  'instructions.nameInvalid': '名称只能包含字母、数字、点、下划线和短横线。',
  'instructions.nameTaken': '名为“{name}”的指令已存在。',
  'instructions.installTitle': '安装 {name}',
  'instructions.agent': '智能体',
  'instructions.agents': '智能体',
  'instructions.noAgentSelected': '请至少选择一个智能体。',
  'instructions.noSupportedAgent': '所选智能体均不支持当前级别。',
  'instructions.level': '级别',
  'instructions.levelUser': '用户级',
  'instructions.levelProject': '项目级',
  'instructions.projectDir': '项目目录',
  'instructions.projectDirRequired': '项目级安装需要提供项目目录。',
  'instructions.installButton': '安装',
  'instructions.installing': '安装中…',
}

const dictionaries: Record<Language, Record<string, string>> = { en, zh }

export function getStoredLanguage(): Language {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (value === 'en' || value === 'zh') return value
  } catch {
    // localStorage unavailable (SSR/tests) — fall through to default.
  }
  return 'en'
}

function persistLanguage(language: Language) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', language)
  }
  try {
    localStorage.setItem(STORAGE_KEY, language)
  } catch {
    // ignore persistence failures
  }
}

// translate looks up a key in the active language, falls back to English, then
// to the raw key. {placeholder} tokens are replaced from `vars`.
export function translate(language: Language, key: string, vars?: Record<string, string | number>): string {
  const template = dictionaries[language][key] ?? dictionaries.en[key] ?? key
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (match, name) => (name in vars ? String(vars[name]) : match))
}

type LanguageContextValue = {
  language: Language
  setLanguage: (language: Language) => void
  toggle: () => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

const LanguageContext = createContext<LanguageContextValue | undefined>(undefined)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(getStoredLanguage)

  useEffect(() => { persistLanguage(language) }, [language])

  const setLanguage = useCallback((next: Language) => setLanguageState(next), [])
  const toggle = useCallback(() => setLanguageState((current) => (current === 'en' ? 'zh' : 'en')), [])

  const value = useMemo<LanguageContextValue>(() => ({
    language,
    setLanguage,
    toggle,
    t: (key, vars) => translate(language, key, vars),
  }), [language, setLanguage, toggle])

  return createElement(LanguageContext.Provider, { value }, children)
}

// useLanguage returns the active language context. Outside a provider it falls
// back to a standalone English translator so components (and isolated tests)
// keep working without a wrapping provider.
export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext)
  if (ctx) return ctx
  return {
    language: 'en',
    setLanguage: () => {},
    toggle: () => {},
    t: (key, vars) => translate('en', key, vars),
  }
}
