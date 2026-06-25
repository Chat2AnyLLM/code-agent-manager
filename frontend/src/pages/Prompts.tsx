import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { Prompt, PromptSource } from '../services/types'
import { Page } from './Page'
import { ExpandableTable, type Column } from '../components/ExpandableTable'
import { Pagination } from '../components/Pagination'
import { useTranslation } from 'react-i18next'

const PAGE_SIZE = 20

export function Prompts() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<Prompt[]>([])
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [status, setStatus] = useState('')
  const [sources, setSources] = useState<PromptSource[]>([])
  const [selectedSource, setSelectedSource] = useState('')

  const load = useCallback(async (q: string, source: string, signal?: AbortSignal) => {
    setLoading(true)
    try {
      let items: Prompt[]
      if (q) {
        items = await api.searchPrompts(q, source)
      } else {
        items = await api.listPrompts(source)
      }
      if (!signal?.aborted) setItems(items)
    } catch (err) {
      if (!signal?.aborted) setStatus(t('prompts.loadFailed', { error: err instanceof Error ? err.message : String(err) }))
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [t])

  useEffect(() => {
    const controller = new AbortController()
    void load(query, selectedSource, controller.signal)
    return () => controller.abort()
  }, [load, query, selectedSource])

  useEffect(() => {
    void api.getPromptSources().then(setSources).catch(() => setSources([]))
  }, [])

  async function syncPrompts(source?: string) {
    setSyncing(true)
    setStatus('')
    try {
      const result = await api.syncPrompts(source)
      setStatus(t('prompts.synced', { count: result.synced }))
      await load(query, selectedSource)
    } catch (err) {
      setStatus(t('prompts.syncFailed', { error: err instanceof Error ? err.message : String(err) }))
    } finally {
      setSyncing(false)
    }
  }

  const paged = items.slice(offset, offset + PAGE_SIZE)
  const totalPages = Math.ceil(items.length / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  const columns: Column<Prompt>[] = [
    { header: t('prompts.colSource'), cell: (p) => <span className="badge">{sourceLabel(p.source)}</span> },
    { header: t('prompts.colCategory'), cell: (p) => p.category || '—' },
    { header: t('prompts.colTitle'), cell: (p) => <strong>{p.title}</strong> },
    { header: t('prompts.colDescription'), cell: (p) => (
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as const }}>
        {p.description || '—'}
      </span>
    ) },
    { header: t('prompts.colAuthor'), cell: (p) => p.author || '—' },
  ]

  return <Page title={t('prompts.title')} description={t('prompts.description')}>
    <div className="inline-form">
      <input
        aria-label={t('prompts.searchPlaceholder')}
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOffset(0) }}
        placeholder={t('prompts.searchPlaceholder')}
      />
      {query && <button onClick={() => { setQuery(''); setOffset(0) }}>{t('library.reset')}</button>}
      <select
        value={selectedSource}
        onChange={(e) => { setSelectedSource(e.target.value); setOffset(0) }}
        aria-label={t('prompts.filterSource')}
      >
        <option value="">{t('prompts.allSources')}</option>
        {sources.map((s) => (
          <option key={s.source} value={s.source}>{s.name} ({s.prompt_count})</option>
        ))}
      </select>
      <button className="primary" onClick={() => void syncPrompts()} disabled={syncing}>
        {syncing ? t('prompts.syncing') : t('prompts.syncAll')}
      </button>
    </div>
    {status && <p className="status-line" role="status">{status}</p>}
    <p className="status-line">{t('prompts.total', { count: items.length })}</p>
    <ExpandableTable
      ariaLabel={t('prompts.title')}
      columns={columns}
      rows={paged}
      rowKey={(p) => String(p.id)}
      empty={<p>{t('prompts.empty')}</p>}
      renderExpanded={(p) => (
        <div className="detail-panel">
          <div className="prompt-actions" style={{ marginBottom: '0.5rem' }}>
            {p.source_url && (
              <a href={p.source_url} target="_blank" rel="noopener noreferrer" style={{ marginRight: '0.5rem' }}>
                {t('prompts.viewSource')}
              </a>
            )}
            <button onClick={() => {
              void navigator.clipboard.writeText(p.content)
              setStatus(t('prompts.copied'))
            }}>
              {t('prompts.copyPrompt')}
            </button>
          </div>
          {p.tags && <p style={{ fontSize: '0.85em', color: '#888' }}>{t('prompts.tags')}: {p.tags}</p>}
          <pre className="detail-content" style={{ whiteSpace: 'pre-wrap' }}>{p.content}</pre>
        </div>
      )}
    />
    <Pagination
      currentPage={currentPage}
      totalPages={totalPages}
      disabled={loading}
      previousLabel={t('library.previous')}
      nextLabel={t('library.next')}
      summaryLabel={t('library.pagination', { current: currentPage, total: totalPages, count: items.length })}
      onPageChange={(page) => setOffset((page - 1) * PAGE_SIZE)}
    />
  </Page>
}

function sourceLabel(source: string): string {
  switch (source) {
    case 'awesome_prompts': return 'Awesome Prompts'
    default: return source
  }
}
