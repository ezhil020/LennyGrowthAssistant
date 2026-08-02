import { useEffect, useState } from 'react'
import { useChatStore } from '../store/chatStore'

export function Sidebar() {
  const { sessions, activeSessionId, fetchSessions, createNewSession, loadSession, deleteSession } = useChatStore()
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null)

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">✨</div>
          <div>
            <div className="sidebar-logo-text">Lenny Growth</div>
            <div className="sidebar-logo-sub">Assistant</div>
          </div>
        </div>
        <button className="btn-new-chat" onClick={() => createNewSession()}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          New Chat
        </button>
      </div>

      <div className="sidebar-section-label">Recent Conversations</div>
      
      <div className="sidebar-sessions">
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`session-item ${activeSessionId === session.id ? 'active' : ''}`}
            onClick={() => loadSession(session.id)}
          >
            <div className="session-icon">💬</div>
            <div className="session-info">
              <div className="session-title" title={session.title}>{session.title}</div>
              <div className="session-date">
                {new Date(session.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
              </div>
            </div>
            <button 
              className="btn-delete-session"
              onClick={(e) => {
                e.stopPropagation()
                setSessionToDelete(session.id)
              }}
              title="Delete chat"
            >
              &times;
            </button>
          </div>
        ))}
      </div>

      {sessionToDelete && (
        <div className="modal-overlay" onClick={() => setSessionToDelete(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Delete Chat</h3>
            <p>Are you sure you want to delete this chat? This action cannot be undone.</p>
            <div className="modal-actions">
              <button className="modal-btn modal-btn-cancel" onClick={() => setSessionToDelete(null)}>
                Cancel
              </button>
              <button className="modal-btn modal-btn-danger" onClick={() => {
                deleteSession(sessionToDelete)
                setSessionToDelete(null)
              }}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
