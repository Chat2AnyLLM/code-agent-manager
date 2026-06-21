import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useTools, useResolvedModels, useApplyConfig } from '../hooks'
import { useProvidersQuery } from '../lib'
import { Page } from './Page'
import { ExpandableTable, type Column } from '../components/ExpandableTable'

const commandOverrides: Record<string, string> = {
  claude: 'claude --allow-dangerously-skip-permissions --dangerously-skip-permissions',
  codex: 'codex --yolo',
}

type AgentCommand = { name: string; command: string; description: string; enabled: boolean; installed: boolean; version: string; runCommand: string }

const PREF_KEY = 'cam.agentSelection'
type AgentSelection = Record<string, { provider: string; model: string }>

function loadPrefs(): AgentSelection {
  try {
    const raw = localStorage.getItem(PREF_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as AgentSelection
      const out: AgentSelection = {}
      for (const [k, v] of Object.entries(parsed)) {
        out[k] = typeof v === 'string' ? { provider: v, model: '' } : v
      }
      return out
    }
  } catch {}
  return {}
}

function savePrefs(prefs: AgentSelection) {
  try { localStorage.setItem(PREF_KEY, JSON.stringify(prefs)) } catch {}
}

export function Agents() {
  const { t } = useTranslation()
  const { tools, isLoading: toolsLoading, install, upgrade, isPending: toolsPending } = useTools()
  const { data: providers = [], isLoading: providersLoading } = useProvidersQuery()
  const { apply, isPending: applyPending } = useApplyConfig()
  const [prefs, setPrefs] = useState<AgentSelection>(() => loadPrefs())
  const [applyStatus, setApplyStatus] = useState<Record<string, { state: 'idle' | 'applying' | 'done' | 'error'; message: string }>>({})
  const [lifecycleStatus, setLifecycleStatus] = useState<Record<string, { state: 'idle' | 'running' | 'done' | 'error'; action: 'install' | 'upgrade'; message: string }>>({})

  const providersByName = useMemo(() => {
    const map = new Map<string, typeof providers[0]>()
    for (const p of providers) map.set(p.name, p)
    return map
  }, [providers])

  const commands = useMemo<AgentCommand[]>(() => tools.map((tool) => ({
    ...tool,
    runCommand: commandOverrides[tool.command] ?? tool.command,
  })), [tools])

  function selectProvider(toolName: string, providerName: string) {
    setPrefs((current) => {
      const prev = current[toolName] ?? { provider: '', model: '' }
      const provider = providersByName.get(providerName)
      const models = provider?.models ?? []
      const model = models.includes(prev.model) ? prev.model : ''
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

  async function applyConfig(toolName: string) {
    const sel = prefs[toolName]
    if (!sel?.provider) {
      setApplyStatus((s) => ({ ...s, [toolName]: { state: 'error', message: t('agents.pickProviderFirst') } }))
      return
    }
    setApplyStatus((s) => ({ ...s, [toolName]: { state: 'applying', message: t('agents.applying') } }))
    try {
      const result = await apply(toolName, sel.provider, sel.model)
      const message = result.configPath === ''
        ? t('agents.noConfigTarget')
        : t('agents.applied', { path: result.configPath, count: String(result.writes.length) })
      setApplyStatus((s) => ({ ...s, [toolName]: { state: 'done', message } }))
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setApplyStatus((s) => ({ ...s, [toolName]: { state: 'error', message: t('agents.applyFailed', { error: message }) } }))
    }
  }

  async function runLifecycle(toolName: string, action: 'install' | 'upgrade') {
    setLifecycleStatus((s) => ({ ...s, [toolName]: { state: 'running', action, message: action === 'install' ? t('agents.installing') : t('agents.upgrading') } }))
    try {
      const result = action === 'install' ? await install(toolName) : await upgrade(toolName)
      setLifecycleStatus((s) => ({ ...s, [toolName]: { state: 'done', action, message: action === 'install' ? t('agents.installDone', { name: toolName }) : t('agents.upgradeDone', { name: toolName }) } }))
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      const label = action === 'install' ? t('agents.install') : t('agents.upgrade')
      setLifecycleStatus((s) => ({ ...s, [toolName]: { state: 'error', action, message: t('agents.lifecycleFailed', { action: label, error: message }) } }))
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
      const models = provider?.models ?? []
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
    { header: 'Status', cell: (tool) => (
      <div className="agent-status-cell">
        <span className={`badge ${tool.installed ? 'badge-installed' : 'badge-not-installed'}`}>{tool.installed ? t('agents.installed') : t('agents.notInstalled')}</span>
        <span>{tool.installed ? t('agents.detected', { version: tool.version }) : t('agents.notDetected')}</span>
      </div>
    ) },
    { header: 'Command', cell: (tool) => <code>{tool.runCommand}</code> },
    { header: t('agents.apply'), cell: (tool) => {
      const status = applyStatus[tool.name]
      const busy = status?.state === 'applying' || applyPending
      return (
        <div className="agent-row-actions">
          <button
            className={tool.installed ? undefined : 'primary'}
            onClick={() => void runLifecycle(tool.name, tool.installed ? 'upgrade' : 'install')}
            disabled={lifecycleStatus[tool.name]?.state === 'running' || toolsPending}
          >
            {lifecycleStatus[tool.name]?.state === 'running'
              ? lifecycleStatus[tool.name].action === 'install' ? t('agents.installing') : t('agents.upgrading')
              : tool.installed ? t('agents.upgrade') : t('agents.install')}
          </button>
          <button onClick={() => void applyConfig(tool.name)} disabled={busy}>
            {busy ? t('agents.applying') : t('agents.apply')}
          </button>
          {status && status.state !== 'idle' && (
            <span className={`agent-apply-status ${status.state}`}>
              {status.message}
            </span>
          )}
          {lifecycleStatus[tool.name] && lifecycleStatus[tool.name].state !== 'idle' && lifecycleStatus[tool.name].state !== 'running' && (
            <span className={`agent-lifecycle-status ${lifecycleStatus[tool.name].state}`}>
              {lifecycleStatus[tool.name].message}
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
