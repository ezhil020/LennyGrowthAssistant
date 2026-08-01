import { useEffect, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatPane } from './components/ChatPane'
import { ArtifactPane } from './components/ArtifactPane'
import { WelcomeScreen } from './components/WelcomeScreen'
import { useChatStore } from './store/chatStore'
import { configApi, healthApi, ProviderInfo, HealthStatus } from './api/client'

function App() {
  const { activeSessionId } = useChatStore()
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [health, setHealth] = useState<HealthStatus | null>(null)

  useEffect(() => {
    const init = async () => {
      try {
        const { data } = await configApi.getProviders()
        setProviders(data.providers)
        const { data: healthData } = await healthApi.check()
        setHealth(healthData)
      } catch (error) {
        console.error('Failed to fetch initial config', error)
      }
    }
    init()
  }, [])

  const handleProviderSwitch = async (name: string) => {
    try {
      await configApi.setProvider(name)
      const { data } = await configApi.getProviders()
      setProviders(data.providers)
    } catch (error) {
      console.error('Failed to switch provider', error)
    }
  }

  return (
    <div className="app-layout">
      <Sidebar />

      {/* main-area stacks the status bar on top, then the content below */}
      <div className="main-area">
        {/* Top Status Bar — always visible, never overlapped */}
        <div className="top-status-bar">
          <div className="health-badge" title={health ? JSON.stringify(health.checks, null, 2) : 'Checking...'}>
            <div className={`health-dot ${health ? (health.status === 'ok' ? 'ok' : 'error') : 'checking'}`} />
            System {health?.status || 'Checking'}
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="text-muted text-sm">Provider:</span>
            {providers.map(p => (
              <button
                key={p.name}
                className="provider-toggle"
                onClick={() => handleProviderSwitch(p.name)}
                style={{ borderColor: p.is_active ? 'rgba(0,212,170,0.5)' : '' }}
              >
                <div className={`provider-dot ${p.name}`} style={{ opacity: p.is_active ? 1 : 0.25 }} />
                {p.name.charAt(0).toUpperCase() + p.name.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* content-area fills the remaining vertical space */}
        <div className="content-area">
          {activeSessionId ? (
            <>
              <ChatPane />
              <ArtifactPane />
            </>
          ) : (
            <WelcomeScreen />
          )}
        </div>
      </div>
    </div>
  )
}

export default App
