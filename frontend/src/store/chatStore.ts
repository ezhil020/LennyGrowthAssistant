import { create } from 'zustand'
import { Session, Message, Artifact, sessionsApi, artifactsApi, SourceAttribution } from '../api/client'

interface ChatState {
  // Session state
  sessions: Session[]
  activeSessionId: string | null
  activeSession: Session | null
  
  // Chat state
  messages: Message[]
  isGenerating: boolean
  
  // Artifact state
  activeArtifact: Artifact | null
  isArtifactVisible: boolean
  
  // Actions
  fetchSessions: () => Promise<void>
  createNewSession: () => Promise<void>
  loadSession: (id: string) => Promise<void>
  sendMessage: (content: string) => Promise<void>
  closeArtifact: () => void
  openArtifact: (id: string) => Promise<void>
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  activeSession: null,
  messages: [],
  isGenerating: false,
  activeArtifact: null,
  isArtifactVisible: false,

  fetchSessions: async () => {
    try {
      const { data } = await sessionsApi.list()
      set({ sessions: data.sessions })
    } catch (error) {
      console.error('Failed to fetch sessions:', error)
    }
  },

  createNewSession: async () => {
    try {
      const { data: session } = await sessionsApi.create()
      set((state) => ({
        sessions: [session, ...state.sessions],
        activeSessionId: session.id,
        activeSession: session,
        messages: [],
        activeArtifact: null,
        isArtifactVisible: false,
      }))
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  },

  loadSession: async (id: string) => {
    try {
      const { data } = await sessionsApi.get(id)
      set({
        activeSessionId: id,
        activeSession: data.session,
        messages: data.messages,
        activeArtifact: null,
        isArtifactVisible: false,
      })
      // If there are artifacts in the history, we could optionally open the latest one
    } catch (error) {
      console.error('Failed to load session:', error)
    }
  },

  sendMessage: async (content: string) => {
    const { activeSessionId } = get()
    if (!activeSessionId) return

    // Optimistic user message
    const userMsgId = Date.now().toString()
    const tempUserMessage: Message = {
      id: userMsgId,
      session_id: activeSessionId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }

    set((state) => ({
      messages: [...state.messages, tempUserMessage],
      isGenerating: true,
    }))

    try {
      // SSE connection
      const response = await fetch(`/api/v1/sessions/${activeSessionId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, stream: true }),
      })

      if (!response.body) throw new Error('No readable stream')

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let done = false

      // Create a temporary assistant message that we'll append tokens to
      const assistantMsgId = `asst_${Date.now()}`
      set((state) => ({
        messages: [
          ...state.messages,
          {
            id: assistantMsgId,
            session_id: activeSessionId,
            role: 'assistant',
            content: '',
            created_at: new Date().toISOString(),
          }
        ]
      }))

      let buffer = ''
      while (!done) {
        const { value, done: readerDone } = await reader.read()
        done = readerDone
        if (value) {
          buffer += decoder.decode(value, { stream: true })
          
          // Process SSE lines
          const lines = buffer.split('\n\n')
          buffer = lines.pop() || '' // Keep the last incomplete chunk in the buffer

          for (const line of lines) {
            if (!line.trim()) continue
            
            const parts = line.split('\n')
            const eventLine = parts.find(p => p.startsWith('event: '))
            const dataLine = parts.find(p => p.startsWith('data: '))
            
            if (eventLine && dataLine) {
              const eventType = eventLine.replace('event: ', '').trim()
              const dataStr = dataLine.replace('data: ', '').trim()
              let data: any
              try {
                data = JSON.parse(dataStr)
              } catch (e) {
                console.error('Failed to parse SSE data', dataStr)
                continue
              }

              if (eventType === 'token') {
                set((state) => ({
                  messages: state.messages.map((m) => 
                    m.id === assistantMsgId ? { ...m, content: m.content + data.text } : m
                  )
                }))
              } else if (eventType === 'sources') {
                set((state) => ({
                  messages: state.messages.map((m) => 
                    m.id === assistantMsgId ? { ...m, sources: data as SourceAttribution } : m
                  )
                }))
              } else if (eventType === 'artifact') {
                const artifactData = data as Artifact
                set((state) => ({ 
                  activeArtifact: artifactData, 
                  isArtifactVisible: true,
                  messages: state.messages.map((m) => 
                    m.id === assistantMsgId ? { ...m, artifact_id: artifactData.id } : m
                  )
                }))
              } else if (eventType === 'routing') {
                set((state) => ({
                  messages: state.messages.map((m) => 
                    m.id === assistantMsgId ? { ...m, skill_used: data.skill_chosen, routing_intent: data.intent } : m
                  )
                }))
              } else if (eventType === 'session_title') {
                set((state) => ({
                  sessions: state.sessions.map((s) => s.id === activeSessionId ? { ...s, title: data.title } : s),
                  activeSession: state.activeSession ? { ...state.activeSession, title: data.title } : null
                }))
              } else if (eventType === 'error') {
                set((state) => ({
                  messages: state.messages.map((m) => 
                    m.id === assistantMsgId ? { ...m, content: m.content + `\n\n[Error: ${data.message}]` } : m
                  )
                }))
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error)
    } finally {
      set({ isGenerating: false })
      get().fetchSessions() // Refresh session list (mostly for title updates)
    }
  },

  closeArtifact: () => set({ isArtifactVisible: false }),
  
  openArtifact: async (id: string) => {
    try {
      const { data } = await artifactsApi.get(id)
      set({ activeArtifact: data, isArtifactVisible: true })
    } catch (error) {
      console.error('Failed to fetch artifact:', error)
    }
  }
}))
