import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Bot, Send, User, Zap, AlertCircle, Clock } from 'lucide-react'
import { sendChatMessage } from '../api/ai'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import type { ChatMessage } from '../types'

const SUGGESTED_PROMPTS = [
  'Show highest risk shipments',
  'Summarize today\'s disruptions',
  'What routes should I avoid?',
  'Which carriers are underperforming?',
  'What is the current geopolitical risk level?',
]

function getOrCreateSessionId(): string {
  const key = 'sc_chat_session'
  let id = localStorage.getItem(key)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(key, id)
  }
  return id
}

export default function AIAssistantPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hello! I\'m your AI supply chain assistant. I can help you analyze risks, summarize disruptions, and answer questions about your shipments. What would you like to know?',
      timestamp: new Date().toISOString(),
    },
  ])
  const [input, setInput] = useState('')
  const [sessionId] = useState(getOrCreateSessionId)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMutation = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (data) => {
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        latency_ms: data.latency_ms,
        fallback_used: data.fallback_used,
      }
      setMessages((prev) => [...prev, assistantMsg])
    },
    onError: () => {
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMsg])
    },
  })

  const handleSend = (text?: string) => {
    const message = (text || input).trim()
    if (!message || sendMutation.isPending) return

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')

    sendMutation.mutate({ session_id: sessionId, message })
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem-3rem)] -m-6 mt-0">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-card/50 backdrop-blur shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-accent-blue/20 flex items-center justify-center">
            <Bot size={18} className="text-accent-blue" />
          </div>
          <div>
            <h1 className="text-text-primary font-semibold">AI Assistant</h1>
            <p className="text-text-muted text-xs">Powered by Gemini · Session: {sessionId.slice(0, 8)}</p>
          </div>
          <div className="ml-auto flex items-center gap-1.5 text-xs text-accent-green">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
            Online
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
          >
            {/* Avatar */}
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === 'user'
                  ? 'bg-accent-blue/20'
                  : 'bg-surface border border-border'
              }`}
            >
              {msg.role === 'user' ? (
                <User size={14} className="text-accent-blue" />
              ) : (
                <Bot size={14} className="text-text-secondary" />
              )}
            </div>

            {/* Bubble */}
            <div className={`max-w-[75%] space-y-1 ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-accent-blue text-white rounded-tr-sm'
                    : 'bg-card border border-border text-text-primary rounded-tl-sm'
                }`}
              >
                {msg.content}
              </div>
              <div className={`flex items-center gap-2 text-xs text-text-muted ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                {msg.latency_ms && (
                  <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {msg.latency_ms}ms
                  </span>
                )}
                {msg.fallback_used && (
                  <span className="flex items-center gap-1 text-accent-amber">
                    <AlertCircle size={10} />
                    Fallback
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {sendMutation.isPending && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-surface border border-border flex items-center justify-center shrink-0">
              <Bot size={14} className="text-text-secondary" />
            </div>
            <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex items-center gap-2">
                <LoadingSpinner size="sm" />
                <span className="text-text-muted text-sm">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested prompts */}
      {messages.length <= 1 && (
        <div className="px-6 pb-3 shrink-0">
          <p className="text-text-muted text-xs mb-2">Suggested prompts:</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => handleSend(prompt)}
                className="text-xs px-3 py-1.5 rounded-full bg-surface border border-border text-text-secondary hover:text-text-primary hover:border-accent-blue/50 transition-colors"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="px-6 py-4 border-t border-border bg-card/50 backdrop-blur shrink-0">
        <div className="flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask about shipments, risks, disruptions..."
            className="input flex-1"
            disabled={sendMutation.isPending}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || sendMutation.isPending}
            className="btn-primary px-4 flex items-center gap-2 disabled:opacity-50"
          >
            {sendMutation.isPending ? <LoadingSpinner size="sm" /> : <Send size={16} />}
          </button>
        </div>
        <p className="text-text-muted text-xs mt-2 text-center">
          <Zap size={10} className="inline mr-1" />
          AI responses may not always be accurate. Verify critical decisions independently.
        </p>
      </div>
    </div>
  )
}
