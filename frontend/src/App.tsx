import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Activity, Bot, FileCog, FileText, HeartPulse, Languages, Moon, Plug, Puzzle, Settings as SettingsIcon, Server, Sparkles, Sun, Users, MessageSquare } from 'lucide-react'
import { Agents } from './pages/Agents'
import { Providers } from './pages/Providers'
import { MCP } from './pages/MCP'
import { Library } from './pages/Library'
import { Instructions } from './pages/Instructions'
import { Configuration } from './pages/Configuration'
import { Diagnostics } from './pages/Diagnostics'
import { Settings } from './pages/Settings'
import { Prompts } from './pages/Prompts'
import { useTheme } from './services/theme'

type Route = 'agents' | 'providers' | 'mcp' | 'instructions' | 'skills' | 'subagents' | 'plugins' | 'config' | 'diagnostics' | 'settings' | 'prompts'

const nav: { route: Route; labelKey: string; icon: typeof Bot }[] = [
  { route: 'providers', labelKey: 'nav.providers', icon: Server },
  { route: 'agents', labelKey: 'nav.agents', icon: Bot },
  { route: 'mcp', labelKey: 'nav.mcp', icon: Plug },
  { route: 'instructions', labelKey: 'nav.instructions', icon: FileText },
  { route: 'skills', labelKey: 'nav.skills', icon: Sparkles },
  { route: 'prompts', labelKey: 'nav.prompts', icon: MessageSquare },
  { route: 'subagents', labelKey: 'nav.subagents', icon: Users },
  { route: 'plugins', labelKey: 'nav.plugins', icon: Puzzle },
  { route: 'config', labelKey: 'nav.config', icon: FileCog },
  { route: 'diagnostics', labelKey: 'nav.diagnostics', icon: HeartPulse },
  { route: 'settings', labelKey: 'nav.settings', icon: SettingsIcon },
]

const ROUTES: Route[] = ['providers', 'agents', 'mcp', 'instructions', 'skills', 'prompts', 'subagents', 'plugins', 'config', 'diagnostics', 'settings']

function readInitialRoute(): Route {
  try {
    const saved = localStorage.getItem('cam.route')
    if (saved && ROUTES.includes(saved as Route)) return saved as Route
  } catch { /* localStorage unavailable */ }
  return 'agents'
}

function Shell() {
  const [route, setRoute] = useState<Route>(readInitialRoute)
  const { theme, toggle } = useTheme()
  const { t, i18n } = useTranslation()

  function navigate(r: Route) {
    setRoute(r)
    try { localStorage.setItem('cam.route', r) } catch { /* ignore */ }
  }

  function toggleLanguage() {
    const next = i18n.language === 'en' ? 'zh' : 'en'
    i18n.changeLanguage(next)
    try { localStorage.setItem('cam.lang', next) } catch { /* ignore */ }
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><Activity /> <span>{t('brand')}</span></div>
      <nav>{nav.map((item) => { const Icon = item.icon; return <button key={item.route} className={route === item.route ? 'active' : ''} onClick={() => navigate(item.route)}><Icon size={18} />{t(item.labelKey)}</button> })}</nav>
      <div className="spacer" />
      <div className="sidebar-footer">
        <button onClick={toggleLanguage} aria-label="Toggle language" lang={i18n.language === 'en' ? 'zh' : 'en'}>
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
      {route === 'instructions' && <Instructions />}
      {route === 'skills' && <Library kind="skill" />}
      {route === 'prompts' && <Prompts />}
      {route === 'subagents' && <Library kind="agent" />}
      {route === 'plugins' && <Library kind="plugin" />}
      {route === 'config' && <Configuration />}
      {route === 'diagnostics' && <Diagnostics />}
      {route === 'settings' && <Settings />}
    </div>
  </div>
}

export function App() {
  return <Shell />
}

export default App
