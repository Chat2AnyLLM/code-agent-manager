import { Page } from './Page'
import { ExpandableTable, type Column } from '../components/ExpandableTable'

type SettingRow = { name: string; summary: string; detail: string }

const rows: SettingRow[] = [
  { name: 'Appearance', summary: 'Theme follows system preferences.', detail: 'A persistent theme toggle can be wired to AppService.SetTheme.' },
  { name: 'About', summary: 'code-agent-manager desktop shares providers, MCP servers, config, and library stores with the CLI.', detail: 'The desktop app and the CLI operate on the same SQLite app state.' },
]

export function Settings() {
  const columns: Column<SettingRow>[] = [
    { header: 'Setting', cell: (r) => <strong>{r.name}</strong> },
    { header: 'Summary', cell: (r) => r.summary },
  ]
  return <Page title="Settings" description="Configure desktop preferences and view application metadata.">
    <ExpandableTable
      ariaLabel="Settings"
      columns={columns}
      rows={rows}
      rowKey={(r) => r.name}
      renderExpanded={(r) => <p>{r.detail}</p>}
    />
  </Page>
}
