import { useEffect, useState, type ComponentType } from 'react'
import './App.css'
import {
  ClipboardCheckIcon,
  Logo,
  SearchIcon,
  ShieldAlertIcon,
  UserPlusIcon,
} from './components/Icons'
import { parseRoute, screenHref, type Screen } from './routes'
import { AddEncounter } from './screens/AddEncounter'
import { HighRiskQueue } from './screens/HighRiskQueue'
import { SearchPatient } from './screens/SearchPatient'
import { StatusTracking, type UpdateLogEntry } from './screens/StatusTracking'

const NAV: { screen: Screen; label: string; icon: ComponentType<{ size?: number }> }[] = [
  { screen: 'add', label: 'Add Encounter', icon: UserPlusIcon },
  { screen: 'search', label: 'Search Patient', icon: SearchIcon },
  { screen: 'high-risk', label: 'High-Risk Queue', icon: ShieldAlertIcon },
  { screen: 'status', label: 'Status Tracking', icon: ClipboardCheckIcon },
]

function App() {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash))
  // Lives here so the update list survives switching between screens.
  const [updateLog, setUpdateLog] = useState<UpdateLogEntry[]>([])

  useEffect(() => {
    const onHashChange = () => setRoute(parseRoute(window.location.hash))
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href={screenHref('search')}>
            <Logo />
            <div>
              <div className="brand-title">Diabetes Patient Management</div>
              <div className="brand-subtitle">Readmission Intervention Queue</div>
            </div>
          </a>
        </div>
        <nav className="tabs" aria-label="Screens">
          {NAV.map(({ screen, label, icon: Icon }) => (
            <a
              key={screen}
              href={screenHref(screen)}
              className={`tab${route.screen === screen ? ' active' : ''}`}
              aria-current={route.screen === screen ? 'page' : undefined}
            >
              <Icon size={16} />
              <span>{label}</span>
            </a>
          ))}
        </nav>
      </header>

      <main className="content">
        {route.screen === 'add' && <AddEncounter />}
        {route.screen === 'search' && <SearchPatient />}
        {route.screen === 'high-risk' && <HighRiskQueue />}
        {route.screen === 'status' && (
          <StatusTracking
            encounterId={route.encounterId}
            updateLog={updateLog}
            onUpdated={(entry) => setUpdateLog((log) => [entry, ...log])}
          />
        )}
      </main>

      <footer className="footer">Learning prototype — not for clinical decision-making.</footer>
    </div>
  )
}

export default App
