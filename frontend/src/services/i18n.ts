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
  'nav.prompts': 'Prompts',
  'nav.skills': 'Skills',
  'nav.subagents': 'Subagents',
  'nav.plugins': 'Plugins',
  'nav.config': 'Configuration',
  'nav.diagnostics': 'Diagnostics',
  'nav.settings': 'Settings',

  // Agents (runnable code agents) page
  'agents.title': 'Agents',
  'agents.description': 'Coding agents CAM manages. Run each from your terminal with the command shown after configuring providers, MCP servers, prompts, skills, subagents, and plugins.',
  'agents.detected': 'Detected: {version}',
  'agents.notDetected': 'Not detected on PATH',
  'agents.installedResources': 'Installed resources',
  'agents.provider': 'Provider',
  'agents.model': 'Model',
  'agents.apply': 'Apply',
  'agents.applying': 'Applying…',
  'agents.applied': 'Applied → {path} ({count} keys)',
  'agents.applyFailed': 'Apply failed: {error}',
  'agents.noConfigTarget': 'This agent has no config file to write.',
  'agents.pickProviderFirst': 'Pick a provider and model first.',

  // Library (prompts/skills/subagents/plugins) pages
  'library.prompts.title': 'Prompts',
  'library.prompts.description': 'Search, install, and refresh reusable prompts from the metadata index.',
  'library.skills.title': 'Skills',
  'library.skills.description': 'Search, install, and refresh Claude-style skills from the metadata index.',
  'library.agents.title': 'Subagents',
  'library.agents.description': 'Search, install, and refresh custom subagents from the metadata index.',
  'library.plugins.title': 'Plugins',
  'library.plugins.description': 'Search, install, and refresh assistant plugins from the metadata index.',
  'library.searchPlaceholder': 'Search {kind}',
  'library.search': 'Search',
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
  'nav.prompts': '提示词',
  'nav.skills': '技能',
  'nav.subagents': '子智能体',
  'nav.plugins': '插件',
  'nav.config': '配置',
  'nav.diagnostics': '诊断',
  'nav.settings': '设置',

  // Agents page
  'agents.title': '智能体',
  'agents.description': 'CAM 管理的编程智能体。配置好服务商、MCP 服务器、提示词、技能、子智能体和插件后，在终端使用下方命令运行各智能体。',
  'agents.detected': '已检测：{version}',
  'agents.notDetected': '未在 PATH 中检测到',
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
  'library.prompts.title': '提示词',
  'library.prompts.description': '从元数据索引中搜索、安装并刷新可复用的提示词。',
  'library.skills.title': '技能',
  'library.skills.description': '从元数据索引中搜索、安装并刷新 Claude 风格的技能。',
  'library.agents.title': '子智能体',
  'library.agents.description': '从元数据索引中搜索、安装并刷新自定义子智能体。',
  'library.plugins.title': '插件',
  'library.plugins.description': '从元数据索引中搜索、安装并刷新助手插件。',
  'library.searchPlaceholder': '搜索{kind}',
  'library.search': '搜索',
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
