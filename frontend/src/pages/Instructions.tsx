import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { api } from '../services/api'
import type { Instruction, InstructionInstall, InstructionTarget } from '../services/types'
import { Page } from './Page'
import { ExpandableTable, type Column } from '../components/ExpandableTable'
import { MultiSelect } from '../components/MultiSelect'
import { useTranslation } from 'react-i18next'
import { instructionSchema, type InstructionFormData } from '../lib/schemas'
import { extractErrorMessage } from '../lib/errors'

export function Instructions() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Instruction[]>([])
  const [targets, setTargets] = useState<InstructionTarget[]>([])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('')
  const [copyNotice, setCopyNotice] = useState(false)
  const [editing, setEditing] = useState<Instruction | null>(null)
  const [creating, setCreating] = useState(false)
  const [projectDirModal, setProjectDirModal] = useState<{ instruction: Instruction; apps: string[]; level: 'user' | 'project' } | null>(null)

  const reload = useCallback(async () => {
    try {
      const list = await api.listInstructions()
      setItems(list ?? [])
    } catch (err) {
      setStatus(extractErrorMessage(err))
    }
  }, [])

  useEffect(() => { void reload() }, [reload])
  useEffect(() => { void api.instructionTargets().then(setTargets).catch(() => setTargets([])) }, [])

  const filtered = query.trim()
    ? items.filter((it) => `${it.name} ${it.description}`.toLowerCase().includes(query.trim().toLowerCase()))
    : items

  async function onUninstall(installId: number) {
    try {
      await api.uninstallInstruction(installId)
      await reload()
    } catch (err) {
      setStatus(extractErrorMessage(err))
    }
  }

  function noteCopyFallback(install: InstructionInstall) {
    if (install.link_kind === 'copy' && !copyNotice) setCopyNotice(true)
  }

  async function onDelete(instruction: Instruction) {
    // eslint-disable-next-line no-alert
    if (typeof window !== 'undefined' && !window.confirm(t('instructions.confirmDelete'))) return
    try {
      await api.deleteInstruction(instruction.id)
      await reload()
    } catch (err) {
      setStatus(extractErrorMessage(err))
    }
  }

  async function doInstall(instruction: Instruction, apps: string[], level: 'user' | 'project', projectDir?: string) {
    setStatus('')
    try {
      const installable = targets.filter((tg) => apps.includes(tg.app)).filter((tg) => {
        return level === 'user' ? tg.supports.user : tg.supports.project
      })
      if (installable.length === 0) {
        setStatus(t('instructions.noSupportedAgent'))
        return
      }
      for (const tg of installable) {
        const install = await api.installInstruction(instruction.id, { app: tg.app, level, project_dir: level === 'project' ? projectDir : undefined })
        if (install.link_kind === 'copy' && !copyNotice) setCopyNotice(true)
      }
      await reload()
    } catch (err) {
      setStatus(extractErrorMessage(err))
    }
  }

  const columns: Column<Instruction>[] = [
    { header: t('instructions.colName'), cell: (it) => <span className="row-name">{it.name}</span> },
    { header: t('instructions.colDescription'), cell: (it) => <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical' as const }}>{it.description || t('library.noDescription')}</span> },
    { header: t('instructions.colInstalled'), cell: (it) => (
      <div className="badges" aria-label={t('instructions.colInstalled')}>
        {(it.installs ?? []).length === 0
          ? <span className="badge badge-not-installed">{t('instructions.notInstalled')}</span>
          : (it.installs ?? []).map((ins) => <InstalledChip key={ins.id} install={ins} onUninstall={onUninstall} />)}
      </div>
    ) },
    { header: t('instructions.colActions'), cell: (it) => (
      <RowActions
        instruction={it}
        targets={targets}
        onEdit={() => setEditing(it)}
        onDelete={() => onDelete(it)}
        onInstall={doInstall}
        onError={setStatus}
      />
    ) },
  ]

  return <Page title={t('instructions.title')} description={t('instructions.description')}>
    <div className="inline-form">
      <input aria-label={t('instructions.searchPlaceholder')} value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('instructions.searchPlaceholder')} />
      {query && <button onClick={() => setQuery('')}>{t('library.reset')}</button>}
      <button className="primary" onClick={() => setCreating(true)}>{t('instructions.new')}</button>
    </div>
    {copyNotice && <p className="status-line" role="status">{t('instructions.copyFallbackBanner')}</p>}
    {status && <p className="status-line error-text" role="alert">{status}</p>}
    <ExpandableTable
      ariaLabel={t('instructions.title')}
      columns={columns}
      rows={filtered}
      rowKey={(it) => String(it.id)}
      empty={<p>{t('instructions.empty')}</p>}
      renderExpanded={(it) => (
        <div className="detail-panel">
          <pre className="detail-content">{it.content || t('library.noDescription')}</pre>
          {(it.installs ?? []).length > 0 && (
            <ul className="install-list">
              {(it.installs ?? []).map((ins) => (
                <li key={ins.id}>{ins.app} ({ins.level}) → <code>{ins.target_path}</code>{ins.link_kind === 'copy' ? ` [${t('instructions.copyBadge')}]` : ''}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    />
    {(creating || editing) && (
      <EditorModal
        instruction={editing}
        existingNames={items.map((it) => it.name)}
        onClose={() => { setCreating(false); setEditing(null) }}
        onSaved={async () => { setCreating(false); setEditing(null); await reload() }}
        onError={setStatus}
      />
    )}
    {projectDirModal && (
      <ProjectDirModal
        instruction={projectDirModal.instruction}
        apps={projectDirModal.apps}
        level={projectDirModal.level}
        targets={targets}
        onClose={() => setProjectDirModal(null)}
        onInstall={async (projectDir) => {
          setProjectDirModal(null)
          await doInstall(projectDirModal.instruction, projectDirModal.apps, projectDirModal.level, projectDir)
        }}
      />
    )}
  </Page>
}

type InstalledChipProps = { install: InstructionInstall; onUninstall: (id: number) => void }

function InstalledChip({ install, onUninstall }: InstalledChipProps) {
  const { t } = useTranslation()
  const isCopy = install.link_kind === 'copy'
  return (
    <span className={`badge badge-installed${isCopy ? ' badge-copy' : ''}`} title={isCopy ? t('instructions.copyTooltip') : install.target_path}>
      {install.app} ({install.level}){isCopy ? ` · ${t('instructions.copyBadge')}` : ''}
      <button type="button" className="chip-remove" aria-label={t('instructions.uninstall', { app: install.app, level: install.level })} onClick={() => onUninstall(install.id)}>×</button>
    </span>
  )
}

type RowActionsProps = {
  instruction: Instruction
  targets: InstructionTarget[]
  onEdit: () => void
  onDelete: () => void
  onInstall: (instruction: Instruction, apps: string[], level: 'user' | 'project', projectDir?: string) => Promise<void>
  onError: (msg: string) => void
}

function RowActions({ instruction, targets, onEdit, onDelete, onInstall }: RowActionsProps) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<string[]>([])
  const [level, setLevel] = useState<'user' | 'project'>('user')
  const [installing, setInstalling] = useState(false)

  const installedApps = (instruction.installs ?? []).map((ins) => ins.app)
  const selectedTargets = targets.filter((tg) => selected.includes(tg.app))
  const supportsUser = selectedTargets.length > 0 && selectedTargets.every((tg) => tg.supports.user)
  const supportsProject = selectedTargets.length > 0 && selectedTargets.every((tg) => tg.supports.project)

  async function doInstall() {
    const apps = selected.length > 0 ? selected : ['claude']
    setInstalling(true)
    try {
      await onInstall(instruction, apps, level)
      setSelected([])
    } catch {
      // status surfaced by parent
    } finally {
      setInstalling(false)
    }
  }

  const installLabel = installing
    ? t('instructions.installing')
    : selected.length > 1
      ? t('library.installToCount', { count: selected.length })
      : t('library.installTo', { target: selected[0] ?? 'claude' })

  return (
    <div className="row-actions">
      <MultiSelect
        options={targets.map((tg) => ({ value: tg.app, label: tg.app, installed: installedApps.includes(tg.app) }))}
        value={selected}
        onChange={setSelected}
        placeholder={t('library.selectTargets')}
        triggerAriaLabel={t('library.selectAgentsFor', { name: instruction.name })}
        listboxAriaLabel={t('library.installTargets', { name: instruction.name })}
      />
      <select
        className="level-select"
        value={level}
        onChange={(e) => setLevel(e.target.value as 'user' | 'project')}
        aria-label={t('instructions.level')}
      >
        <option value="user">{t('instructions.levelUser')}</option>
        <option value="project" disabled={!supportsProject}>{t('instructions.levelProject')}</option>
      </select>
      <button className="primary" onClick={doInstall} disabled={installing}>{installLabel}</button>
      <button onClick={onEdit}>{t('instructions.edit')}</button>
      <button className="danger" onClick={onDelete}>{t('instructions.delete')}</button>
    </div>
  )
}

type ProjectDirModalProps = {
  instruction: Instruction
  apps: string[]
  level: 'user' | 'project'
  targets: InstructionTarget[]
  onClose: () => void
  onInstall: (projectDir: string) => Promise<void>
}

function ProjectDirModal({ instruction, onClose, onInstall }: ProjectDirModalProps) {
  const { t } = useTranslation()
  const [projectDir, setProjectDir] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!projectDir.trim()) return
    setBusy(true)
    try {
      await onInstall(projectDir)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-label={t('instructions.installTitle', { name: instruction.name })} onClick={(e) => e.stopPropagation()}>
        <h2>{t('instructions.installTitle', { name: instruction.name })}</h2>
        <label>
          {t('instructions.projectDir')}
          <input aria-label={t('instructions.projectDir')} value={projectDir} onChange={(e) => setProjectDir(e.target.value)} placeholder="/path/to/project" />
        </label>
        <div className="modal-actions">
          <button className="primary" onClick={submit} disabled={busy || !projectDir.trim()}>{busy ? t('instructions.installing') : t('instructions.installButton')}</button>
          <button onClick={onClose}>{t('instructions.cancel')}</button>
        </div>
      </div>
    </div>
  )
}

type EditorModalProps = {
  instruction: Instruction | null
  existingNames: string[]
  onClose: () => void
  onSaved: () => Promise<void>
  onError: (msg: string) => void
}

function EditorModal({ instruction, existingNames, onClose, onSaved, onError }: EditorModalProps) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<InstructionFormData>({
    resolver: zodResolver(instructionSchema),
    defaultValues: {
      name: instruction?.name ?? '',
      description: instruction?.description ?? '',
      content: instruction?.content ?? '',
    },
  })

  async function onSubmit(data: InstructionFormData) {
    const taken = existingNames.some((n) => n === data.name && n !== instruction?.name)
    if (taken) {
      onError(t('instructions.nameTaken', { name: data.name }))
      return
    }

    setBusy(true)
    try {
      if (instruction) await api.updateInstruction(instruction.id, data)
      else await api.createInstruction(data)
      await onSaved()
    } catch (err) {
      onError(extractErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-label={instruction ? t('instructions.editTitle') : t('instructions.newTitle')} onClick={(e) => e.stopPropagation()}>
        <h2>{instruction ? t('instructions.editTitle') : t('instructions.newTitle')}</h2>
        <form onSubmit={handleSubmit(onSubmit)}>
          <label>
            {t('instructions.name')}
            <input aria-label={t('instructions.name')} {...register('name')} />
            {errors.name && <span className="error-text">{errors.name.message}</span>}
          </label>
          <label>
            {t('instructions.descriptionLabel')}
            <input aria-label={t('instructions.descriptionLabel')} {...register('description')} />
          </label>
          <label>
            {t('instructions.content')}
            <textarea aria-label={t('instructions.content')} rows={20} {...register('content')} />
          </label>
          <div className="modal-actions">
            <button type="submit" className="primary" disabled={busy}>{busy ? t('instructions.saving') : t('instructions.save')}</button>
            <button type="button" onClick={onClose}>{t('instructions.cancel')}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
