import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { MCPRegistryItem } from '../services/types'
import { Page } from './Page'
import { ExpandableTable, type Column } from '../components/ExpandableTable'
import { MultiSelect } from '../components/MultiSelect'
import { Pagination } from '../components/Pagination'
import { useTranslation } from 'react-i18next'

// MCP mirrors the Library (skill/plugin) pages: it lists every *discovered* MCP
// server from the bundled registry in a table, with a per-row dropdown of code
// agents (MCP clients) to install each server to. The registry is bounded and
// bundled, so search/filter/pagination all happen client-side (the skills page
// paginates server-side only because its metadata index is unbounded).
const PAGE_SIZE = 20

function registrySourceUrl(item: MCPRegistryItem): string | undefined {
  return item.repoUrl || item.homepage
}

export function MCP() {
  const { t } = useTranslation()
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

  const load = useCallback(async (q: string, signal?: AbortSignal) => {
    setLoading(true)
    try {
      const items = await api.searchMCPRegistry(q)
      if (!signal?.aborted) setItems(items)
    } catch (err) {
      if (!signal?.aborted) setStatus(t('mcp.searchFailed', { error: err instanceof Error ? err.message : String(err) }))
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [t])

  useEffect(() => {
    const controller = new AbortController()
    void load(query, controller.signal)
    return () => controller.abort()
  }, [load, query])

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

  async function uninstallFrom(item: MCPRegistryItem, clients: string[]) {
    setStatus('')
    try {
      await api.uninstallMCPServer(item.name, clients)
      setStatus(t('mcp.uninstalled', { name: item.name, targets: clients.join(', ') }))
      await load(query)
    } catch (err) {
      setStatus(t('mcp.uninstallFailed', { error: err instanceof Error ? err.message : String(err) }))
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
    { header: 'Name', cell: (item) => {
      const href = registrySourceUrl(item)
      const label = item.displayName || item.name
      return <h3 className="row-name">{href
        ? <a className="source-link" href={href} target="_blank" rel="noopener noreferrer" title={`Open ${label} source on GitHub`}>{label}</a>
        : label}
      </h3>
    } },
    { header: 'Source', cell: (item) => {
      const href = registrySourceUrl(item)
      if (!href) return <span className="repo-link">{item.name}</span>
      return <a className="repo-link" href={href} target="_blank" rel="noopener noreferrer" title={`Open ${href}`}>{href.replace(/^https?:\/\//, '').replace(/\/$/, '')}</a>
    } },
    { header: 'Status', cell: (item) => {
      const installedClients = item.installedClients ?? []
      return installedClients.length > 0
        ? <div className="badges" aria-label={t('mcp.installedClients')}>{installedClients.map((app) => <span key={app} className="badge badge-installed">{app}</span>)}</div>
        : <div className="badges"><span className="badge badge-not-installed">{t('mcp.notInstalled')}</span></div>
    } },
    { header: 'Actions', cell: (item) => <MCPActions item={item} targets={targets} onInstall={installTo} onUninstall={uninstallFrom} /> },
  ]

  return <Page title={t('mcp.title')} description={t('mcp.description')}>
    <div className="inline-form">
      <input aria-label={t('mcp.searchPlaceholder')} value={query} onChange={(event) => { setQuery(event.target.value); setOffset(0) }} placeholder={t('mcp.searchPlaceholder')} />
      <button onClick={() => { setOffset(0); load(query) }} disabled={loading}>{t('mcp.search')}</button>
      {(query || installedOnly) && <button onClick={() => { setQuery(''); setInstalledOnly(false); setOffset(0) }}>{t('library.reset')}</button>}
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
    <Pagination
      currentPage={currentPage}
      totalPages={pageCount}
      disabled={loading}
      previousLabel={t('library.previous')}
      nextLabel={t('library.next')}
      summaryLabel={t('library.pagination', { current: currentPage, total: pageCount, count: visibleItems.length })}
      onPageChange={(page) => setOffset((page - 1) * PAGE_SIZE)}
    />
  </Page>
}

type MCPActionsProps = {
  item: MCPRegistryItem
  targets: string[]
  onInstall: (item: MCPRegistryItem, clients: string[]) => Promise<void>
  onUninstall: (item: MCPRegistryItem, clients: string[]) => Promise<void>
}

// MCPActions renders the install-target picker and install/uninstall buttons
// inside a row's Actions cell, mirroring Library's ResourceActions.
function MCPActions({ item, targets, onInstall, onUninstall }: MCPActionsProps) {
  const { t } = useTranslation()
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

  async function doUninstall() {
    const clients = selected.length > 0 ? selected : installedClients
    if (clients.length === 0) return
    setInstalling(true)
    try {
      await onUninstall(item, clients)
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
      {installedClients.length > 0 && (
        <button className="danger" onClick={doUninstall} disabled={installing}>{t('mcp.uninstall')}</button>
      )}
    </div>
  )
}
