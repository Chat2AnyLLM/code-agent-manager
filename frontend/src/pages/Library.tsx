import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import type { Entity, MetadataItem, MetadataDetail } from '../services/types'
import { Page } from './Page'
import { useLanguage } from '../services/i18n'

// Each kind maps to its own i18n title/description keys. The "agent" kind is
// labelled "Subagents" in the UI to distinguish installable subagent resources
// from the runnable code agents shown on the Agents page.
const titleKeys: Record<Entity['kind'], string> = {
  prompt: 'library.prompts.title',
  skill: 'library.skills.title',
  agent: 'library.agents.title',
  plugin: 'library.plugins.title',
}

const descriptionKeys: Record<Entity['kind'], string> = {
  prompt: 'library.prompts.description',
  skill: 'library.skills.description',
  agent: 'library.agents.description',
  plugin: 'library.plugins.description',
}

const PAGE_SIZE = 20

type LibraryProps = {
  kind: Entity['kind']
}

export function Library({ kind }: LibraryProps) {
  const { t } = useLanguage()
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<MetadataItem[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [installedOnly, setInstalledOnly] = useState(false)
  const [status, setStatus] = useState('')
  const [targets, setTargets] = useState<string[]>([])
  const autoRefreshed = useRef(false)

  const title = t(titleKeys[kind])
  const kindLabel = title.toLowerCase()

  useEffect(() => { void api.metadataTargets(kind).then(setTargets) }, [kind])

  const load = useCallback(async (q: string, off: number) => {
    setLoading(true)
    try {
      const resp = await api.searchMetadata(kind, q, PAGE_SIZE, off)
      setItems(resp.items ?? [])
      setTotal(resp.total ?? 0)
      return resp
    } catch (err) {
      setStatus(`Search failed: ${err instanceof Error ? err.message : String(err)}`)
      return null
    } finally {
      setLoading(false)
    }
  }, [kind])

  // On first load, auto-refresh once when the index needs it. Two cases qualify:
  //   1. Empty — a fresh machine that has never refreshed.
  //   2. Stale — rows left by an older binary that indexed at the repo level
  //      (install_key "owner/repo", no colon) instead of the resource level
  //      ("owner/repo:resource"). Such rows massively undercount a kind (e.g.
  //      one "agents" row standing in for hundreds of agents) and would never
  //      self-heal under a purely empty check, because the kind isn't empty.
  const loadOrAutoRefresh = useCallback(async (q: string, off: number) => {
    const resp = await load(q, off)
    const respItems = resp?.items ?? []
    const isEmpty = !resp || resp.total === 0
    const isStale = respItems.length > 0 && respItems.some((item) => !item.install_key.includes(':'))
    if ((isEmpty || isStale) && q === '' && off === 0 && !autoRefreshed.current) {
      autoRefreshed.current = true
      setRefreshing(true)
      try {
        await api.refreshMetadata()
        await load(q, off)
      } catch {
        // Leave the existing state; the manual Refresh button remains available.
      } finally {
        setRefreshing(false)
      }
    }
  }, [load])

  useEffect(() => { void loadOrAutoRefresh(query, offset) }, [loadOrAutoRefresh, query, offset])

  async function refresh() {
    setRefreshing(true)
    setStatus('')
    try {
      const summary = await api.refreshMetadata()
      setStatus(`Refreshed: ${summary.items_added} items from ${summary.sources_scanned} sources`)
      setOffset(0)
      await load(query, 0)
    } catch (err) {
      setStatus(`Refresh failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setRefreshing(false)
    }
  }

  async function installTo(item: MetadataItem, apps: string[]) {
    setStatus('')
    try {
      await api.installMetadata(item.kind, item.install_key, apps)
      setStatus(`Installed ${item.name} to ${apps.join(', ')}`)
      await load(query, offset)
    } catch (err) {
      setStatus(`Install failed: ${err instanceof Error ? err.message : String(err)}`)
      throw err
    }
  }

  const pageCount = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1
  // "Installed only" filters the loaded page so users can see, at a glance, what
  // they have installed and to which agents. It narrows the current view rather
  // than issuing a server-side query (the index has no installed filter yet).
  const visibleItems = installedOnly ? items.filter((item) => (item.installed_apps ?? []).length > 0) : items

  return <Page title={title} description={t(descriptionKeys[kind])}>
    <div className="inline-form">
      <input aria-label={`${title} ${t('library.search')}`} value={query} onChange={(event) => { setQuery(event.target.value); setOffset(0) }} placeholder={t('library.searchPlaceholder', { kind: kindLabel })} />
      <button onClick={() => load(query, offset)} disabled={loading}>{t('library.search')}</button>
      <button onClick={refresh} disabled={refreshing}>{refreshing ? t('library.refreshing') : t('library.refresh')}</button>
      <label className="filter-toggle">
        <input type="checkbox" checked={installedOnly} onChange={(event) => setInstalledOnly(event.target.checked)} />
        {t('library.installedOnly')}
      </label>
    </div>
    {status && <p className="status-line" role="status">{status}</p>}
    <div className="cards">
      {visibleItems.length === 0 && !loading && <p>{t('library.empty', { kind: kindLabel })}</p>}
      {visibleItems.map((item) => <ResourceCard key={`${item.kind}-${item.install_key}`} item={item} targets={targets} onInstall={installTo} />)}
    </div>
    {pageCount > 1 && (
      <nav className="pagination" aria-label="pagination">
        <button onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0 || loading}>{t('library.previous')}</button>
        <span>{t('library.pagination', { current: currentPage, total: pageCount, count: total })}</span>
        <button onClick={() => setOffset(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= total || loading}>{t('library.next')}</button>
      </nav>
    )}
  </Page>
}

type ResourceCardProps = {
  item: MetadataItem
  targets: string[]
  onInstall: (item: MetadataItem, apps: string[]) => Promise<void>
}

function ResourceCard({ item, targets, onInstall }: ResourceCardProps) {
  const { t } = useLanguage()
  const installedApps = item.installed_apps ?? []
  const [selected, setSelected] = useState<string[]>([])
  const [installing, setInstalling] = useState(false)
  const [expanded, setExpanded] = useState(false)

  function toggle(app: string) {
    setSelected((current) => current.includes(app) ? current.filter((a) => a !== app) : [...current, app])
  }

  async function doInstall() {
    const apps = selected.length > 0 ? selected : ['claude']
    setInstalling(true)
    try {
      await onInstall(item, apps)
      setSelected([])
    } catch {
      // status surfaced by parent
    } finally {
      setInstalling(false)
    }
  }

  const installLabel = installing
    ? t('library.installing')
    : selected.length > 1
      ? t('library.installToCount', { count: selected.length })
      : t('library.installTo', { target: selected[0] ?? 'claude' })

  return <article className="card">
    <div className="card-head">
      <h2>{item.name}</h2>
      <button className="link-button" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
        {expanded ? t('library.collapse') : t('library.expand')}
      </button>
    </div>
    <p className="card-desc">{item.description || t('library.noDescription')}</p>
    <small>{item.repo_owner}/{item.repo_name}{item.repo_branch && item.repo_branch !== 'main' ? `@${item.repo_branch}` : ''}</small>
    {installedApps.length > 0
      ? <div className="badges" aria-label={t('library.installedAgents')}>{installedApps.map((app) => <span key={app} className="badge badge-installed">{app}</span>)}</div>
      : <div className="badges"><span className="badge badge-not-installed">{t('library.notInstalled')}</span></div>}
    <details className="agent-picker-details">
      <summary>{t('library.selectTargets')}{selected.length > 0 ? ` (${selected.length})` : ''}</summary>
      <div className="agent-picker" aria-label={t('library.installTargets', { name: item.name })}>
        {targets.map((app) => {
          const isInstalled = installedApps.includes(app)
          return <label key={app} className={`agent-chip${selected.includes(app) ? ' selected' : ''}${isInstalled ? ' installed' : ''}`}>
            <input type="checkbox" checked={selected.includes(app)} onChange={() => toggle(app)} aria-label={`${app}${isInstalled ? ' (installed)' : ''}`} />
            {app}{isInstalled ? ' ✓' : ''}
          </label>
        })}
      </div>
    </details>
    <button className="primary" onClick={doInstall} disabled={installing}>{installLabel}</button>
    {expanded && <DetailPanel item={item} />}
  </article>
}

// DetailPanel lazily fetches the item's full metadata and manifest content the
// first time a card is expanded, then renders the manifest (SKILL.md/AGENT.md/
// plugin.json) below the indexed fields. Fetch is on-demand because it hits the
// network for the source repo; collapsing and re-expanding reuses the result.
function DetailPanel({ item }: { item: MetadataItem }) {
  const { t } = useLanguage()
  const [detail, setDetail] = useState<MetadataDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    setFailed(false)
    api.metadataDetail(item.kind, item.install_key)
      .then((result) => { if (active) setDetail(result) })
      .catch(() => { if (active) setFailed(true) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [item.kind, item.install_key])

  return <section className="detail-panel" aria-label={`details for ${item.name}`}>
    <dl className="detail-meta">
      <div><dt>kind</dt><dd>{item.kind}</dd></div>
      <div><dt>repo</dt><dd>{item.repo_owner}/{item.repo_name}</dd></div>
      <div><dt>branch</dt><dd>{item.repo_branch || 'main'}</dd></div>
      <div><dt>install key</dt><dd><code>{item.install_key}</code></dd></div>
      <div><dt>targets</dt><dd>{item.target_apps}</dd></div>
    </dl>
    {loading && <p>{t('library.loadingDetail')}</p>}
    {failed && <p className="error-text">{t('library.detailFailed')}</p>}
    {detail && !loading && <>
      {detail.manifest_path && <small>{t('library.manifestPath', { path: detail.manifest_path })}</small>}
      {detail.content
        ? <pre className="detail-content">{detail.content}</pre>
        : !failed && <p>{t('library.detailFailed')}</p>}
    </>}
  </section>
}
