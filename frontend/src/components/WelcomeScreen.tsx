import { useChatStore } from '../store/chatStore'

export function WelcomeScreen() {
  const { createNewSession } = useChatStore()

  const handleStart = (initialMessage?: string) => {
    // In a full implementation, you might want to pass the initialMessage 
    // to the chat pane after creating the session. For simplicity here,
    // we just create a new session.
    createNewSession()
  }

  return (
    <div className="welcome-screen">
      <div className="welcome-logo">✦</div>
      <div>
        <h1 className="welcome-title">Lenny Growth Assistant</h1>
        <p className="welcome-subtitle">
          AI-powered product and growth insights grounded strictly in Lenny's Podcast transcripts.
        </p>
      </div>

      <div className="welcome-cards">
        <div className="welcome-card" onClick={() => handleStart()}>
          <div className="welcome-card-icon">⬡</div>
          <div className="welcome-card-title">Expert Q&A</div>
          <div className="welcome-card-desc">Ask specific questions about retention, PLG, and product-market fit.</div>
        </div>
        <div className="welcome-card" onClick={() => handleStart()}>
          <div className="welcome-card-icon">✍️</div>
          <div className="welcome-card-title">Ship30for30 Essays</div>
          <div className="welcome-card-desc">Synthesize insights into high-impact, skimmable essays.</div>
        </div>
        <div className="welcome-card" onClick={() => handleStart()}>
          <div className="welcome-card-icon">◈</div>
          <div className="welcome-card-title">Artifact Generation</div>
          <div className="welcome-card-desc">Create HTML dashboards and Markdown documents on the fly.</div>
        </div>
      </div>

      <button className="btn-start" onClick={() => handleStart()}>
        Start Chatting
      </button>
    </div>
  )
}
