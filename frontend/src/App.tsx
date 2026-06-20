import { useState } from 'react'
import { Activity, Bot, FileCog, FileText, HeartPulse, Languages, Moon, Plug, Puzzle, Settings as SettingsIcon, Server, Sparkles, Sun, Users } from 'lucide-react'
import { Agents } from './pages/Agents'
import { Providers } from './pages/Providers'
import { MCP } from './pages/MCP'
import { Library } from './pages/Library'
import { Configuration } from './pages/Configuration'
import { Diagnostics } from './pages/Diagnostics'
import { Settings } from './pages/Settings'
import { useTheme } from './services/theme'
import { LanguageProvider, useLanguage } from './services/i18n'

type Route = 'agents' | 'providers' | 'mcp' | 'instructions' | 'skills' | 'subagents' | 'plugins' | 'config' | 'diagnostics' | 'settings'

const nav: { route: Route; labelKey: string; icon: typeof Bot }[] = [
  { route: 'providers', labelKey: 'nav.providers', icon: Server },
  { route: 'agents', labelKey: 'nav.agents', icon: Bot },
  { route: 'mcp', labelKey: 'nav.mcp', icon: Plug },
  { route: 'instructions', labelKey: 'nav.instructions', icon: FileText },
  { route: 'skills', labelKey: 'nav.skills', icon: Sparkles },
  { route: 'subagents', labelKey: 'nav.subagents', icon: Users },
  { route: 'plugins', labelKey: 'nav.plugins', icon: Puzzle },
  { route: 'config', labelKey: 'nav.config', icon: FileCog },
  { route: 'diagnostics', labelKey: 'nav.diagnostics', icon: HeartPulse },
  { route: 'settings', labelKey: 'nav.settings', icon: SettingsIcon },
]

function Shell() {
  const [route, setRoute] = useState<Route>('agents')
  const { theme, toggle } = useTheme()
  const { t, language, toggle: toggleLanguage } = useLanguage()

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><Activity /> <span>{t('brand')}</span></div>
      <nav>{nav.map((item) => { const Icon = item.icon; return <button key={item.route} className={route === item.route ? 'active' : ''} onClick={() => setRoute(item.route)}><Icon size={18} />{t(item.labelKey)}</button> })}</nav>
      <div className="spacer" />
      <div className="sidebar-footer">
        <button onClick={toggleLanguage} aria-label="Toggle language" lang={language === 'en' ? 'zh' : 'en'}>
          <Languages size={18} />
          {t('lang.toggle')}
        </button>
        <button onClick={toggle} aria-label="Toggle theme">
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          {theme === 'dark' ? t('theme.light') : t('theme.dark')}
        </button>
      </div>
    </aside>
    <div className="content">
      {route === 'agents' && <Agents />}
      {route === 'providers' && <Providers />}
      {route === 'mcp' && <MCP />}
      {route === 'instructions' && <Library kind="instruction" />}
      {route === 'skills' && <Library kind="skill" />}
      {route === 'subagents' && <Library kind="agent" />}
      {route === 'plugins' && <Library kind="plugin" />}
      {route === 'config' && <Configuration />}
      {route === 'diagnostics' && <Diagnostics />}
      {route === 'settings' && <Settings />}
    </div>
  </div>
}

export function App() {
  return <LanguageProvider><Shell /></LanguageProvider>
}

export default App
