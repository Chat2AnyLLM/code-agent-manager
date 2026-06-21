import { useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import type { Provider, Tool } from '../services/types'
import { Page } from './Page'
import { ExpandableTable, type Column } from '../components/ExpandableTable'
import { useLanguage } from '../services/i18n'

// Run-command overrides for agents whose recommended invocation differs from the
// bare binary name (e.g. permission-skipping flags used during local dev).
const commandOverrides: Record<string, string> = {
  claude: 'claude --allow-dangerously-skip-permissions --dangerously-skip-permissions',
  codex: 'codex --yolo',
}

type AgentCommand = Tool & { runCommand: string }

// Per-agent selection (provider + model) is a local UI preference: the Agents
// page documents how to run each agent, and the chosen provider/model is the
// one the user intends to point that agent at. It is persisted in localStorage
// so it survives reloads. Clicking "Apply" writes that selection into the
// agent's native config file (the cc-switch "switch" operation) via the
// sidecar — it does not launch the agent.
const PREF_KEY = 'cam.agentSelection'

type AgentSelection = Record<string, { provider: string; model: string }>

function loadPrefs(): AgentSelection {
  try {
    const raw = localStorage.getItem(PREF_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as AgentSelection
      // Migrate the old shape ({ toolName: "providerName" }) if present.
      const out: AgentSelection = {}
      for (const [k, v] of Object.entries(parsed)) {
        out[k] = typeof v === 'string' ? { provider: v, model: '' } : v
      }
      return out
    }
  } catch {
    // localStorage unavailable or corrupt — fall back to empty.
  }
  return {}
}

function savePrefs(prefs: AgentSelection) {
  try { localStorage.setItem(PREF_KEY, JSON.stringify(prefs)) } catch { /* ignore */ }
}

type ApplyState = 'idle' | 'applying' | 'done' | 'error'
type ApplyStatus = { state: ApplyState; message: string }

// Agents lists the coding agents CAM manages, one row per agent in a compact
// table. Each row lets the user pick the provider and model to target, then
// "Apply" writes that provider's config into the agent's native config file
// without launching it. The row expands to show the run command and detection
// status — the "usage and details" a user needs before launching from a
// terminal. This replaces the former card grid.
export function Agents() {
  const { t } = useLanguage()
  const [tools, setTools] = useState<Tool[]>([])
  const [providers, setProviders] = useState<Provider[]>([])
  const [prefs, setPrefs] = useState<AgentSelection>(() => loadPrefs())
  const [applyStatus, setApplyStatus] = useState<Record<string, ApplyStatus>>({})
  // resolvedModels caches the full model list per provider, fetched from the
  // sidecar's /api/providers/{name}/models endpoint. This merges API-discovered
  // models with statically configured ones and built-in defaults — unlike
  // provider.models, which only holds the static list.
  const [resolvedModels, setResolvedModels] = useState<Record<string, string[]>>({})

  useEffect(() => { void api.listTools().then(setTools) }, [])
  useEffect(() => { void api.listProviders().then(setProviders) }, [])

  const providersByName = useMemo(() => {
    const map = new Map<string, Provider>()
    for (const p of providers) map.set(p.name, p)
    return map
  }, [providers])

  // ensureModels fetches and caches the resolved model list for a provider the
  // first time it is needed (on selection or for a previously pinned provider).
  function ensureModels(providerName: string) {
    if (!providerName) return
    setResolvedModels((current) => {
      if (providerName in current) return current
      void api.resolveModels(providerName)
        .then((models) => setResolvedModels((next) => ({ ...next, [providerName]: models })))
        .catch(() => setResolvedModels((next) => ({ ...next, [providerName]: [] })))
      return { ...current, [providerName]: current[providerName] ?? [] }
    })
  }

  // Resolve models for any provider already pinned in saved preferences.
  useEffect(() => {
    for (const sel of Object.values(prefs)) {
      if (sel.provider) ensureModels(sel.provider)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const commands = useMemo<AgentCommand[]>(() => tools.map((tool) => ({
    ...tool,
    runCommand: commandOverrides[tool.command] ?? tool.command,
  })), [tools])

  function selectProvider(toolName: string, providerName: string) {
    ensureModels(providerName)
    setPrefs((current) => {
      const prev = current[toolName] ?? { provider: '', model: '' }
      // If the new provider doesn't offer the currently pinned model, clear it.
      const nextModels = resolvedModels[providerName] ?? providersByName.get(providerName)?.models ?? []
      const model = nextModels.includes(prev.model) ? prev.model : ''
      const next = { ...current, [toolName]: { provider: providerName, model } }
      savePrefs(next)
      return next
    })
  }

  function selectModel(toolName: string, model: string) {
    setPrefs((current) => {
      const prev = current[toolName] ?? { provider: '', model: '' }
      const next = { ...current, [toolName]: { ...prev, model } }
      savePrefs(next)
      return next
    })
  }

  async function apply(toolName: string) {
    const sel = prefs[toolName]
    if (!sel?.provider) {
      setApplyStatus((s) => ({ ...s, [toolName]: { state: 'error', message: t('agents.pickProviderFirst') } }))
      return
    }
    setApplyStatus((s) => ({ ...s, [toolName]: { state: 'applying', message: t('agents.applying') } }))
    try {
      const result = await api.applyConfig(toolName, sel.provider, sel.model)
      const message = result.configPath === ''
        ? t('agents.noConfigTarget')
        : t('agents.applied', { path: result.configPath, count: String(result.writes.length) })
      setApplyStatus((s) => ({ ...s, [toolName]: { state: 'done', message } }))
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setApplyStatus((s) => ({ ...s, [toolName]: { state: 'error', message: t('agents.applyFailed', { error: message }) } }))
    }
  }

  const columns: Column<AgentCommand>[] = [
    { header: t('agents.title'), cell: (tool) => <strong>{tool.name}</strong> },
    { header: t('agents.provider'), cell: (tool) => (
      <select
        aria-label={`${t('agents.provider')} ${tool.name}`}
        value={prefs[tool.name]?.provider ?? ''}
        onChange={(event) => selectProvider(tool.name, event.target.value)}
      >
        <option value="">—</option>
        {providers.map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
      </select>
    ) },
    { header: t('agents.model'), cell: (tool) => {
      const sel = prefs[tool.name]
      const provider = sel?.provider ? providersByName.get(sel.provider) : undefined
      // Prefer the resolved list (API + static + defaults); fall back to the
      // provider's static models while the resolved list is still loading.
      const models = (sel?.provider ? resolvedModels[sel.provider] : undefined) ?? provider?.models ?? []
      // When the provider advertises models, offer a dropdown; otherwise let
      // the user type a model id directly (e.g. a provider with no static list).
      if (models.length > 0) {
        return (
          <select
            aria-label={`${t('agents.model')} ${tool.name}`}
            value={sel?.model ?? ''}
            onChange={(event) => selectModel(tool.name, event.target.value)}
          >
            <option value="">—</option>
            {models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        )
      }
      return (
        <input
          aria-label={`${t('agents.model')} ${tool.name}`}
          type="text"
          placeholder="model id"
          value={sel?.model ?? ''}
          onChange={(event) => selectModel(tool.name, event.target.value)}
        />
      )
    } },
    { header: 'Status', cell: (tool) => tool.installed ? t('agents.detected', { version: tool.version }) : t('agents.notDetected') },
    { header: 'Command', cell: (tool) => <code>{tool.runCommand}</code> },
    { header: t('agents.apply'), cell: (tool) => {
      const status = applyStatus[tool.name]
      const busy = status?.state === 'applying'
      return (
        <div className="agent-apply-cell">
          <button onClick={() => void apply(tool.name)} disabled={busy}>
            {busy ? t('agents.applying') : t('agents.apply')}
          </button>
          {status && status.state !== 'idle' && (
            <span className={`agent-apply-status ${status.state}`}>
              {status.message}
            </span>
          )}
        </div>
      )
    } },
  ]

  return <Page title={t('agents.title')} description={t('agents.description')}>
    <ExpandableTable
      ariaLabel={t('agents.title')}
      columns={columns}
      rows={commands}
      rowKey={(tool) => tool.name}
      renderExpanded={(tool) => (
        <p>{tool.description}</p>
      )}
    />
  </Page>
}
