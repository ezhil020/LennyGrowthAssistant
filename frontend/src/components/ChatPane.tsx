import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChatStore } from '../store/chatStore'
import { Message, SourceAttribution } from '../api/client'

function SourcesPanel({ sources }: { sources: SourceAttribution }) {
  const [isOpen, setIsOpen] = useState(false)
  if (!sources || sources.chunks.length === 0) return null

  return (
    <div className="sources-panel" style={{ marginTop: '12px', marginLeft: '36px' }}>
      <button className="sources-toggle" onClick={() => setIsOpen(!isOpen)}>
        <svg
          width="11" height="11" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: isOpen ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        {sources.chunks.length} sources · {sources.retrieval_mode}
      </button>
      {isOpen && (
        <div className="sources-list">
          {sources.chunks.map((chunk) => (
            <div key={chunk.chunk_id} className="source-chip">
              <div className="source-chip-score">{(chunk.similarity_score * 100).toFixed(0)}%</div>
              <div className="source-chip-meta">
                <div className="source-chip-episode">{chunk.episode_title}</div>
                <a href={chunk.source_url} target="_blank" rel="noreferrer" className="source-chip-link">
                  View Transcript ↗
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ThinkingIndicator() {
  return (
    <div className="message-turn" style={{ animation: 'fadeSlideIn 0.2s ease' }}>
      <div className="turn-header">
        <div className="turn-avatar assistant">✦</div>
        <span className="turn-role assistant">Lenny</span>
      </div>
      <div className="turn-body">
        <div className="thinking-indicator">
          <div className="thinking-dots">
            <div className="thinking-dot" />
            <div className="thinking-dot" />
            <div className="thinking-dot" />
          </div>
          <span className="thinking-label">Thinking…</span>
        </div>
      </div>
    </div>
  )
}

function MessageTurn({ message, isStreaming }: { message: Message; isStreaming?: boolean }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message-turn ${isUser ? 'user' : 'assistant'}`}>
      <div className="turn-header">
        <div className={`turn-avatar ${isUser ? 'user' : 'assistant'}`}>
          {isUser ? 'You' : '✦'}
        </div>
        <span className={`turn-role ${isUser ? 'user' : 'assistant'}`}>
          {isUser ? 'You' : 'Lenny'}
        </span>
        {!isUser && message.skill_used && (
          <div className={`skill-badge ${message.skill_used}`}>
            {message.skill_used === 'qa' && '⬡ Q&A'}
            {message.skill_used === 'ship30' && '✍ Ship30'}
            {message.skill_used === 'artifact' && '◈ Artifact'}
          </div>
        )}
      </div>

      <div className="turn-body">
        {isUser ? (
          <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
        ) : (
          <div className="artifact-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
            {isStreaming && <span className="streaming-cursor" />}
          </div>
        )}
      </div>

      {message.sources && <SourcesPanel sources={message.sources} />}
    </div>
  )
}

export function ChatPane() {
  const { messages, activeSession, isGenerating, sendMessage } = useChatStore()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 140) + 'px'
  }, [input])

  const handleSend = () => {
    if (!input.trim() || isGenerating) return
    sendMessage(input.trim())
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const lastMsg = messages[messages.length - 1]
  const isLastAssistantStreaming = isGenerating && lastMsg?.role === 'assistant'
  const showThinking = isGenerating && lastMsg?.role !== 'assistant'

  if (!activeSession) return null

  return (
    <div className="chat-pane">
      <div className="chat-header">
        <div className="chat-title">{activeSession.title}</div>
      </div>

      <div className="chat-messages">
        <div className="chat-messages-inner">
          {messages.map((msg, i) => (
            <MessageTurn
              key={msg.id}
              message={msg}
              isStreaming={isLastAssistantStreaming && i === messages.length - 1}
            />
          ))}

          {showThinking && <ThinkingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="chat-input-area">
        <div className="chat-input-area-inner">
          <div className="chat-input-wrapper">
            <textarea
              ref={textareaRef}
              className="chat-input"
              placeholder="Message Lenny…"
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
              aria-label="Send message"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          <div className="chat-input-hints">
            <button className="hint-chip" onClick={() => setInput('What did Brian Chesky say about growth?')}>
              Brian Chesky on growth
            </button>
            <button className="hint-chip" onClick={() => setInput('Write a Ship30 post about finding PMF')}>
              Ship30 post on PMF
            </button>
            <button className="hint-chip" onClick={() => setInput('Create an HTML dashboard for retention metrics')}>
              HTML retention dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
