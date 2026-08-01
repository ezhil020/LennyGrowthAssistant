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
    // Fetch initial config and health
    const init = async () => {
      try {
        const { data } = await configApi.getProviders()
        setProviders(data.providers)
        
        const { data: healthData } = await healthApi.check()
        setHealth(healthData)
      } catch (error) {
        console.error("Failed to fetch initial config", error)
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
      console.error("Failed to switch provider", error)
    }
  }

  return (
    <div className="app-layout">
      <Sidebar />
      
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Top Status Bar (Global) */}
        <div style={{ padding: '8px 16px', background: 'var(--bg-surface)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: '16px', alignItems: 'center' }}>
          
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
                style={{ borderColor: p.is_active ? 'var(--accent-primary)' : '' }}
              >
                <div className={`provider-dot ${p.name}`} style={{ opacity: p.is_active ? 1 : 0.2 }} />
                {p.name.charAt(0).toUpperCase() + p.name.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
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
