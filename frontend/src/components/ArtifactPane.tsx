import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChatStore } from '../store/chatStore'

export function ArtifactPane() {
  const { activeArtifact, isArtifactVisible, closeArtifact } = useChatStore()
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview')

  if (!isArtifactVisible || !activeArtifact) {
    return <div className="artifact-pane hidden" />
  }

  return (
    <div className="artifact-pane">
      <div className="artifact-header">
        <div className="artifact-title-row">
          <div className={`artifact-type-badge ${activeArtifact.type}`}>
            {activeArtifact.type}
          </div>
          <div className="artifact-name" title={activeArtifact.title || 'Artifact'}>
            {activeArtifact.title || 'Artifact'}
          </div>
          <div className="artifact-version">v{activeArtifact.version}</div>
        </div>
        
        <div className="artifact-controls">
          <div className="tab-group">
            <button 
              className={`tab-btn ${viewMode === 'preview' ? 'active' : ''}`}
              onClick={() => setViewMode('preview')}
            >
              Preview
            </button>
            <button 
              className={`tab-btn ${viewMode === 'code' ? 'active' : ''}`}
              onClick={() => setViewMode('code')}
            >
              Code
            </button>
          </div>
          <button className="btn-icon" onClick={closeArtifact} title="Close Artifact">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      <div className="artifact-content">
        {viewMode === 'preview' ? (
          activeArtifact.type === 'html' ? (
            <iframe 
              srcDoc={activeArtifact.content} 
              className="artifact-iframe" 
              sandbox="allow-scripts" // Explicitly omit allow-same-origin per SRS
              title="Artifact Preview"
            />
          ) : (
            <div className="artifact-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {activeArtifact.content}
              </ReactMarkdown>
            </div>
          )
        ) : (
          <div className="artifact-code">
            <pre>
              <code>{activeArtifact.content}</code>
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
