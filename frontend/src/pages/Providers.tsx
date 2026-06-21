import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useProviderActions } from '../hooks'
import { Page } from './Page'
import { ExpandableTable, type Column } from '../components/ExpandableTable'
import { providerSchema, type ProviderFormData } from '../lib/schemas'

export function Providers() {
  const { t } = useTranslation()
  const { providers, isLoading, addProvider, updateApiKey, updateApiKeyEnv, toggle, remove, isPending } = useProviderActions()
  const [keyDraft, setKeyDraft] = useState<Record<string, string>>({})
  const [keyStatus, setKeyStatus] = useState<Record<string, string>>({})
  const [envDraft, setEnvDraft] = useState<Record<string, string>>({})
  const [envStatus, setEnvStatus] = useState<Record<string, string>>({})

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ProviderFormData>({
    resolver: zodResolver(providerSchema),
    defaultValues: { name: '', endpoint: '', apiKey: '', apiKeyEnv: '' },
  })

  async function onSubmit(data: ProviderFormData) {
    try {
      await addProvider({ ...data, clients: ['claude'], models: [], enabled: true })
      reset()
    } catch {
      // Error handled by mutation
    }
  }

  async function saveApiKey(providerName: string) {
    const value = keyDraft[providerName] ?? ''
    if (!value) return
    setKeyStatus((s) => ({ ...s, [providerName]: t('providers.apiKeySaving') }))
    try {
      await updateApiKey(providerName, value)
      setKeyDraft((d) => ({ ...d, [providerName]: '' }))
      setKeyStatus((s) => ({ ...s, [providerName]: t('providers.apiKeySaved') }))
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setKeyStatus((s) => ({ ...s, [providerName]: message }))
    }
  }

  async function saveApiKeyEnv(providerName: string) {
    const value = envDraft[providerName] ?? ''
    if (!value) return
    setEnvStatus((s) => ({ ...s, [providerName]: t('providers.apiKeySaving') }))
    try {
      await updateApiKeyEnv(providerName, value)
      setEnvDraft((d) => ({ ...d, [providerName]: '' }))
      setEnvStatus((s) => ({ ...s, [providerName]: t('providers.apiKeySaved') }))
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setEnvStatus((s) => ({ ...s, [providerName]: message }))
    }
  }

  const columns: Column<{ name: string; endpoint: string; models: string[]; enabled: boolean; description: string; maskedApiKey?: string; apiKeyEnv: string; clients: string[] }>[] = [
    { header: 'Name', cell: (p) => <strong>{p.name}</strong> },
    { header: 'Endpoint', cell: (p) => <code>{p.endpoint}</code> },
    { header: 'Models', cell: (p) => p.models.join(', ') || '—' },
    { header: 'Status', cell: (p) => p.enabled ? 'Enabled' : 'Disabled' },
    { header: 'Actions', className: 'row-actions', cell: (p) => (
      <div className="row-actions">
        <button onClick={() => toggle(p.name, !p.enabled)} disabled={isPending}>{p.enabled ? 'Disable' : 'Enable'}</button>
        <button onClick={() => remove(p.name)} disabled={isPending}>Remove</button>
      </div>
    ) },
  ]

  return <Page title="Providers" description="Manage SQLite-backed provider entries, models, API key env vars, and enablement.">
    <section className="card"><h2>Add Provider</h2>
      <form className="inline-form" onSubmit={handleSubmit(onSubmit)}>
        <input aria-label="Provider name" placeholder="name" {...register('name')} />
        {errors.name && <span className="error-text">{errors.name.message}</span>}
        <input aria-label="Provider endpoint" placeholder="https://host/v1" {...register('endpoint')} />
        {errors.endpoint && <span className="error-text">{errors.endpoint.message}</span>}
        <input aria-label={t('providers.apiKey')} type="password" placeholder={t('providers.apiKeyPlaceholder')} title={t('providers.apiKeyHint')} {...register('apiKey')} />
        <input aria-label={t('providers.apiKeyEnv')} placeholder="OPENAI_API_KEY" title={t('providers.apiKeyEnvHint')} {...register('apiKeyEnv')} />
        <button type="submit" disabled={isPending}>Add provider</button>
      </form>
    </section>
    <ExpandableTable
      ariaLabel="Providers"
      columns={columns}
      rows={providers}
      rowKey={(p) => p.name}
      renderExpanded={(p) => (
        <dl className="row-meta">
          <div><dt>{t('providers.description')}</dt><dd>{p.description || '—'}</dd></div>
          <div><dt>{t('providers.apiKeyEnv')}</dt><dd>{p.apiKeyEnv ? <code>{p.apiKeyEnv}</code> : '—'}</dd></div>
          <div><dt>{t('providers.maskedKey')}</dt><dd>{p.maskedApiKey ? <code>{p.maskedApiKey}</code> : '—'}</dd></div>
          <div>
            <dt>{t('providers.setApiKey')}</dt>
            <dd>
              <div className="inline-form">
                <input
                  aria-label={`${t('providers.setApiKey')} ${p.name}`}
                  type="password"
                  placeholder={t('providers.apiKeyPlaceholder')}
                  value={keyDraft[p.name] ?? ''}
                  onChange={(event) => setKeyDraft((d) => ({ ...d, [p.name]: event.target.value }))}
                />
                <button onClick={() => saveApiKey(p.name)} disabled={!(keyDraft[p.name] ?? '').length || isPending}>{t('providers.apiKeySave')}</button>
                {keyStatus[p.name] && <span style={{ fontSize: '0.85em' }}>{keyStatus[p.name]}</span>}
              </div>
            </dd>
          </div>
          <div>
            <dt>{t('providers.setApiKeyEnv')}</dt>
            <dd>
              <div className="inline-form">
                <input
                  aria-label={`${t('providers.setApiKeyEnv')} ${p.name}`}
                  type="text"
                  placeholder="OMNILLM_API_KEY"
                  value={envDraft[p.name] ?? ''}
                  onChange={(event) => setEnvDraft((d) => ({ ...d, [p.name]: event.target.value }))}
                />
                <button onClick={() => saveApiKeyEnv(p.name)} disabled={!(envDraft[p.name] ?? '').length || isPending}>{t('providers.apiKeySave')}</button>
                {envStatus[p.name] && <span style={{ fontSize: '0.85em' }}>{envStatus[p.name]}</span>}
              </div>
            </dd>
          </div>
          <div><dt>{t('providers.clients')}</dt><dd>{p.clients.join(', ') || '—'}</dd></div>
        </dl>
      )}
    />
  </Page>
}
