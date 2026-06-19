import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { MCPRegistryItem } from '../services/types'
import { Page } from './Page'
import { ExpandableTable, type Column } from '../components/ExpandableTable'
import { MultiSelect } from '../components/MultiSelect'
import { useLanguage } from '../services/i18n'

// MCP mirrors the Library (skill/plugin) pages: it lists every *discovered* MCP
// server from the bundled registry in a table, with a per-row dropdown of code
// agents (MCP clients) to install each server to. The registry is bounded and
// bundled, so search/filter/pagination all happen client-side (the skills page
// paginates server-side only because its metadata index is unbounded).
const PAGE_SIZE = 20

export function MCP() {
  const { t } = useLanguage()
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<MCPRegistryItem[]>([])
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [reloading, setReloading] = useState(false)
  const [installedOnly, setInstalledOnly] = useState(false)
  const [status, setStatus] = useState('')
  const [targets, setTargets] = useState<string[]>([])

  // Install targets are the MCP clients (claude, gemini, …) — the analog of
  // Library's apps.
  useEffect(() => { void api.listMCPClients().then((clients) => setTargets(clients.map((c) => c.name))) }, [])

  const load = useCallback(async (q: string) => {
    setLoading(true)
    try {
      setItems(await api.searchMCPRegistry(q))
    } catch (err) {
      setStatus(t('mcp.searchFailed', { error: err instanceof Error ? err.message : String(err) }))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { void load(query) }, [load, query])

  async function reload() {
    setReloading(true)
    setStatus('')
    try {
      setItems(await api.searchMCPRegistry(query))
    } catch (err) {
      setStatus(t('mcp.searchFailed', { error: err instanceof Error ? err.message : String(err) }))
    } finally {
      setReloading(false)
    }
  }

  async function installTo(item: MCPRegistryItem, clients: string[]) {
    setStatus('')
    try {
      await api.installMCPServer(item.name, clients)
      setStatus(t('mcp.installed', { name: item.name, targets: clients.join(', ') }))
      await load(query)
    } catch (err) {
      setStatus(t('mcp.installFailed', { error: err instanceof Error ? err.message : String(err) }))
      throw err
    }
  }

  // "Installed only" narrows the current view to servers already installed in at
  // least one client, mirroring Library's installed-only toggle.
  const visibleItems = installedOnly ? items.filter((item) => (item.installedClients ?? []).length > 0) : items
  // Pagination is client-side over the filtered set (the registry is bounded).
  const pageCount = Math.ceil(visibleItems.length / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1
  const pagedItems = visibleItems.slice(offset, offset + PAGE_SIZE)

  const columns: Column<MCPRegistryItem>[] = [
    { header: 'Name', cell: (item) => <h3 className="row-name">{item.displayName || item.name}</h3> },
    { header: 'Source', cell: (item) => {
      const href = item.repoUrl || item.homepage
      if (!href) return <span className="repo-link">{item.name}</span>
      return <a className="repo-link" href={href} target="_blank" rel="noopener noreferrer" title={`Open ${href}`}>{href.replace(/^https?:\/\//, '').replace(/\/$/, '')}</a>
    } },
    { header: 'Status', cell: (item) => {
      const installedClients = item.installedClients ?? []
      return installedClients.length > 0
        ? <div className="badges" aria-label={t('mcp.installedClients')}>{installedClients.map((app) => <span key={app} className="badge badge-installed">{app}</span>)}</div>
        : <div className="badges"><span className="badge badge-not-installed">{t('mcp.notInstalled')}</span></div>
    } },
    { header: 'Actions', cell: (item) => <MCPActions item={item} targets={targets} onInstall={installTo} /> },
  ]

  return <Page title={t('mcp.title')} description={t('mcp.description')}>
    <div className="inline-form">
      <input aria-label={t('mcp.searchPlaceholder')} value={query} onChange={(event) => { setQuery(event.target.value); setOffset(0) }} placeholder={t('mcp.searchPlaceholder')} />
      <button onClick={() => { setOffset(0); load(query) }} disabled={loading}>{t('mcp.search')}</button>
      <button onClick={reload} disabled={reloading}>{reloading ? t('mcp.reloading') : t('mcp.reload')}</button>
      <label className="filter-toggle">
        <input type="checkbox" checked={installedOnly} onChange={(event) => { setInstalledOnly(event.target.checked); setOffset(0) }} />
        {t('mcp.installedOnly')}
      </label>
    </div>
    {status && <p className="status-line" role="status">{status}</p>}
    <ExpandableTable
      ariaLabel={t('mcp.title')}
      columns={columns}
      rows={pagedItems}
      rowKey={(item) => item.name}
      empty={!loading ? <p>{t('mcp.empty')}</p> : undefined}
      renderExpanded={(item) => (
        <div className="detail-panel">
          <p className="card-desc">{item.description || t('mcp.noDescription')}</p>
          <dl className="detail-meta">
            {item.installType && <div><dt>install</dt><dd>{item.installType}</dd></div>}
            {item.license && <div><dt>license</dt><dd>{item.license}</dd></div>}
            {item.categories && item.categories.length > 0 && <div><dt>categories</dt><dd>{item.categories.join(', ')}</dd></div>}
            {item.tags && item.tags.length > 0 && <div><dt>tags</dt><dd>{item.tags.join(', ')}</dd></div>}
          </dl>
        </div>
      )}
    />
    {pageCount > 1 && (
      <nav className="pagination" aria-label="pagination">
        <button onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0 || loading}>{t('library.previous')}</button>
        <span>{t('library.pagination', { current: currentPage, total: pageCount, count: visibleItems.length })}</span>
        <button onClick={() => setOffset(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= visibleItems.length || loading}>{t('library.next')}</button>
      </nav>
    )}
  </Page>
}

type MCPActionsProps = {
  item: MCPRegistryItem
  targets: string[]
  onInstall: (item: MCPRegistryItem, clients: string[]) => Promise<void>
}

// MCPActions renders the install-target picker and install button inside a row's
// Actions cell, mirroring Library's ResourceActions.
function MCPActions({ item, targets, onInstall }: MCPActionsProps) {
  const { t } = useLanguage()
  const installedClients = item.installedClients ?? []
  const [selected, setSelected] = useState<string[]>([])
  const [installing, setInstalling] = useState(false)

  async function doInstall() {
    const clients = selected.length > 0 ? selected : ['claude']
    setInstalling(true)
    try {
      await onInstall(item, clients)
      setSelected([])
    } catch {
      // status surfaced by parent
    } finally {
      setInstalling(false)
    }
  }

  const installLabel = installing
    ? t('mcp.installing')
    : selected.length > 1
      ? t('mcp.installToCount', { count: selected.length })
      : t('mcp.installTo', { target: selected[0] ?? 'claude' })

  return (
    <div className="row-actions">
      <MultiSelect
        options={targets.map((app) => ({ value: app, label: app, installed: installedClients.includes(app) }))}
        value={selected}
        onChange={setSelected}
        placeholder={t('mcp.selectTargets')}
        triggerAriaLabel={t('mcp.selectAgentsFor', { name: item.name })}
        listboxAriaLabel={t('mcp.installTargets', { name: item.name })}
      />
      <button className="primary" onClick={doInstall} disabled={installing}>{installLabel}</button>
    </div>
  )
}
