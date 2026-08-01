import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChatStore } from '../store/chatStore'
import { Message, SourceAttribution } from '../api/client'

function SourcesPanel({ sources }: { sources: SourceAttribution }) {
  const [isOpen, setIsOpen] = useState(false)
  if (!sources || sources.chunks.length === 0) return null

  return (
    <div className="sources-panel">
      <button className="sources-toggle" onClick={() => setIsOpen(!isOpen)}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: isOpen ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }}>
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
        {sources.chunks.length} Sources ({sources.retrieval_mode})
      </button>
      
      {isOpen && (
        <div className="sources-list">
          {sources.chunks.map((chunk) => (
            <div key={chunk.chunk_id} className="source-chip">
              <div className="source-chip-score">{(chunk.similarity_score * 100).toFixed(0)}%</div>
              <div className="source-chip-meta">
                <div className="source-chip-episode">{chunk.episode_title}</div>
                <a href={chunk.source_url} target="_blank" rel="noreferrer" className="source-chip-link">View Transcript</a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  
  return (
    <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
      <div className={`message-avatar ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? 'U' : '✨'}
      </div>
      <div className="message-content-wrapper">
        {message.skill_used && (
          <div className={`skill-badge ${message.skill_used}`}>
            {message.skill_used === 'qa' && 'Q&A Retrieval'}
            {message.skill_used === 'ship30' && 'Ship30for30 Generator'}
            {message.skill_used === 'artifact' && 'Artifact Generator'}
          </div>
        )}
        
        <div className="message-bubble-body">
          {isUser ? (
            <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
          ) : (
            <div className="artifact-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
        
        {message.sources && <SourcesPanel sources={message.sources} />}
      </div>
    </div>
  )
}

export function ChatPane() {
  const { messages, activeSession, isGenerating, sendMessage } = useChatStore()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || isGenerating) return
    sendMessage(input.trim())
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!activeSession) return null

  return (
    <div className="chat-pane">
      <div className="chat-header">
        <div className="chat-title">{activeSession.title}</div>
      </div>
      
      <div className="chat-messages">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isGenerating && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="message-bubble assistant">
             <div className="message-avatar assistant">✨</div>
             <div className="message-content-wrapper">
               <div className="message-bubble-body skeleton" style={{ width: '200px', height: '40px' }} />
             </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <textarea
            className="chat-input"
            placeholder="Ask Lenny about growth, product, or retention..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isGenerating}
          />
          <button 
            className="btn-send" 
            onClick={handleSend}
            disabled={!input.trim() || isGenerating}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
        <div className="chat-input-hints">
          <button className="hint-chip" onClick={() => setInput('What did Brian Chesky say about growth?')}>Brian Chesky on growth</button>
          <button className="hint-chip" onClick={() => setInput('Write a Ship30 post about finding PMF')}>Ship30 post on PMF</button>
          <button className="hint-chip" onClick={() => setInput('Create an HTML dashboard for retention metrics')}>HTML retention dashboard</button>
        </div>
      </div>
    </div>
  )
}
