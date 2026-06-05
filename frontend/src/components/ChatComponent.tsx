/**
 * ChatComponent — reusable AI financial chat widget.
 * Used by ChatPage and DashboardPage to eliminate duplication.
 * Fully typed, accessible, responsive (320 px → 1920 px+).
 */

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  memo,
  type FormEvent,
} from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, MessageCircle, PlusSquare, RotateCcw } from 'lucide-react'
import { Card } from '@/components/UI'
import { showErrorToast } from '@/utils/toast'
import ConversationsList from './ConversationsList'
import { chatService } from '@/services/chatService'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

// ── Types ──────────────────────────────────────────────────────────────

interface Message {
  readonly id: number
  readonly type: 'user' | 'bot'
  readonly text: string
  readonly timestamp: Date
}

interface ChatComponentProps {
  readonly className?: string
  readonly height?: string
  readonly showFeatures?: boolean
  readonly headerSubtitle?: string
  readonly showSidebar?: boolean
}

// ── Feature Suggestions ────────────────────────────────────────────────

const FEATURE_SUGGESTIONS: readonly string[] = [
  '💰 How to create a budget?',
  '📊 Explain the 50/30/20 rule',
  '🎯 Tips for saving money',
  '🏦 How do EMIs work?',
] as const

// ── Initial Bot Message ────────────────────────────────────────────────

function createInitialMessage(): Message {
  return {
    id: 1,
    type: 'bot',
    text: "Hello! 👋 I'm your Financial Education Assistant. I'm here to help you with budgeting tips, financial advice, and answering questions about your finances. How can I help you today?",
    timestamp: new Date(),
  }
}

// ── Component ──────────────────────────────────────────────────────────

export const ChatComponent = memo<ChatComponentProps>(function ChatComponent({
  className = '',
  height,
  showFeatures = false,
  headerSubtitle = 'Always here to help 💬',
  showSidebar = true,
}) {
  const [messages, setMessages] = useState<readonly Message[]>([createInitialMessage()])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sidebarVisible, setSidebarVisible] = useState<boolean>(() => {
    try {
      // prefer stored preference
      const stored = localStorage.getItem('fe_chat_sidebar')
      if (stored !== null) return stored === 'true'
      return typeof window !== 'undefined' ? window.innerWidth >= 1024 && showSidebar : showSidebar
    } catch {
      return typeof window !== 'undefined' ? window.innerWidth >= 1024 && showSidebar : showSidebar
    }
  })
  // Auto-hide sidebar on small screens and persist user preference
  useEffect(() => {
    try {
      const stored = localStorage.getItem('fe_chat_sidebar')
      if (stored !== null) {
        setSidebarVisible(stored === 'true')
        return
      }
    } catch {
      // ignore
    }
    // default: visible on lg, hidden on smaller
    setSidebarVisible(window.innerWidth >= 1024 && showSidebar)
    const onResize = () => {
      if (window.innerWidth < 1024) setSidebarVisible(false)
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [showSidebar])

  useEffect(() => {
    try { localStorage.setItem('fe_chat_sidebar', sidebarVisible ? 'true' : 'false') } catch {}
  }, [sidebarVisible])

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to latest message
  const scrollToBottom = useCallback((): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Persist conversation id to localStorage for continuity across refreshes.
  // We save only non-temp conversation ids. Loading will verify ownership.
  useEffect(() => {
    try {
      if (conversationId && !conversationId.startsWith('temp-')) {
        localStorage.setItem('fe_chat_conv', conversationId)
      }
    } catch {
      // ignore storage errors
    }
  }, [conversationId])

  // Load server-side user prefs (sidebar visibility)
  useEffect(() => {
    let cancelled = false
    const loadPrefs = async (): Promise<void> => {
      try {
        const res = await fetch('/api/v1/chat/prefs')
        if (!res.ok) return
        const prefs = await res.json()
        if (cancelled) return
        if (prefs?.sidebar !== undefined) setSidebarVisible(Boolean(prefs.sidebar))
      } catch {
        // ignore
      }
    }
    void loadPrefs()
    return () => { cancelled = true }
  }, [])

  // Map backend history messages to local Message type (robust)
  const mapHistoryToMessages = useCallback((historyMessages: any[]): Message[] => {
    return historyMessages.map((m, idx) => {
      const text =
        m?.text ?? m?.content ?? m?.reply ?? m?.message ?? (typeof m === 'string' ? m : JSON.stringify(m))
      const role = (m?.role ?? m?.sender ?? m?.from ?? '').toString().toLowerCase()
      const type = role === 'user' || role === 'human' || role === 'client' ? 'user' : 'bot'
      const timestamp = m?.timestamp ? new Date(m.timestamp) : new Date(Date.now() - (historyMessages.length - idx) * 1000)
      return {
        id: (m?.id ? Number(m.id) : Date.now()) + idx,
        type,
        text,
        timestamp,
      }
    })
  }, [])

  // Load conversation history when conversationId becomes available
  useEffect(() => {
    let cancelled = false
    const load = async (): Promise<void> => {
      if (!conversationId) return
      // Skip loading for temporary client-only ids
      if (conversationId.startsWith('temp-')) return
      try {
        const history = await chatService.getHistory(conversationId)
        if (cancelled) return
        const msgs = mapHistoryToMessages((history as any).messages ?? [])
        if (msgs.length > 0) {
          setMessages(msgs)
        } else {
          setMessages([createInitialMessage()])
        }
      } catch (err: any) {
        const status = err?.response?.status
        if (status === 403) {
          try { localStorage.removeItem('fe_chat_conv') } catch {}
          try {
            const conv = await chatService.createConversation()
            if (!cancelled) setConversationId(conv.id)
          } catch {
            if (!cancelled) setConversationId(`temp-${Date.now()}`)
          }
          return
        }
        // Unknown error: show initial message
        setMessages([createInitialMessage()])
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [conversationId, mapHistoryToMessages])

  // Initialize conversation
  useEffect(() => {
    let cancelled = false
    const init = async (): Promise<void> => {
      try {
        const stored = (() => {
          try { return localStorage.getItem('fe_chat_conv') } catch { return null }
        })()
        if (stored) {
          // if stored is a temp id (local-only) and user is authenticated, attempt migration
          if (stored.startsWith('temp-')) {
            try {
              const payload = { messages: messages.map((m) => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.text, timestamp: m.timestamp.toISOString() })) }
              const data = await chatService.migrateConversation(payload)
              if (!cancelled) setConversationId(data.id)
              return
            } catch {
              // migration failed — fall back to verifying regular stored conv
            }
          }

          // verify server-side ownership by attempting to load history
          try {
            await chatService.getHistory(stored)
            if (!cancelled) setConversationId(stored)
            return
          } catch (err: any) {
            const status = err?.response?.status
            if (status === 403) {
              try { localStorage.removeItem('fe_chat_conv') } catch {}
            }
            // fallthrough to create new
          }
        }

        const conversation = await chatService.createConversation()
        if (!cancelled) setConversationId(conversation.id)
      } catch {
        if (!cancelled) setConversationId(`temp-${Date.now()}`)
      }
    }
    void init()
    return () => {
      cancelled = true
    }
  }, [])

  const handleSendMessage = useCallback(
    async (e: FormEvent): Promise<void> => {
      e.preventDefault()
      const text = inputValue.trim()
      if (!text) return

      const userMessage: Message = {
        id: Date.now(),
        type: 'user',
        text,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMessage])
      setInputValue('')
      setIsLoading(true)
      setError(null)

      try {
        const response = await chatService.sendMessage(text, conversationId)

        const botMessage: Message = {
          id: Date.now() + 1,
          type: 'bot',
          text: response.reply,
          timestamp: new Date(),
        }

        setMessages((prev) => [...prev, botMessage])

        if (response.conversation_id && response.conversation_id !== conversationId) {
          setConversationId(response.conversation_id)
        }
      } catch {
        setError('Failed to get response. Please try again.')
        showErrorToast('Failed to send message')
        // Remove the failed user message
        setMessages((prev) => prev.filter((m) => m.id !== userMessage.id))
      } finally {
        setIsLoading(false)
        inputRef.current?.focus()
      }
    },
    [inputValue, conversationId],
  )

  const handleSuggestionClick = useCallback(
    (suggestion: string): void => {
      setInputValue(suggestion)
      inputRef.current?.focus()
    },
    [],
  )

  const handleClearChat = useCallback((): void => {
    setMessages([createInitialMessage()])
    setError(null)
    // clear conversation data locally; optionally delete backend conv
  }, [])

  const handleNewChat = useCallback(async (): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      const conv = await chatService.createConversation()
      setConversationId(conv.id)
      setMessages([createInitialMessage()])
    } catch (err) {
      showErrorToast('Failed to create new chat')
      // fallback: create a local temp id
      setConversationId(`temp-${Date.now()}`)
      setMessages([createInitialMessage()])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }, [])

  // Render markdown safely (uses marked -> DOMPurify)
  const renderMarkdown = (text: string) => {
    try {
      const rawHtml = md.render(text ?? '')
      const clean = DOMPurify.sanitize(rawHtml)
      return (
        <div
          className="prose prose-sm max-w-full dark:prose-invert text-sm text-gray-700 dark:text-gray-200"
          dangerouslySetInnerHTML={{ __html: clean }}
        />
      )
    } catch (err) {
      // Fallback to simple paragraph rendering if parser fails
      return text.split(/\n\n+/).map((para, i) => (
        <p key={i} className="whitespace-pre-wrap break-words mb-2 last:mb-0 text-sm text-gray-700 dark:text-gray-200">{para}</p>
      ))
    }
  }

  return (
    <div style={{ ['--card-padding' as any]: '0.5rem' }} className="h-full">
      <Card className={`${className} flex h-full`}>
        {showSidebar && (
          <div className="hidden lg:block">
            {sidebarVisible && (
              <div className="w-72 border-r pr-4">
                <ConversationsList
                  active={conversationId}
                  onSelect={(id: string) => {
                    if (id === 'new') return void handleNewChat()
                    setConversationId(id)
                  }}
                  onDelete={async (id: string) => {
                    try {
                      await chatService.deleteConversation(id)
                      // refresh list by toggling conversationId
                      if (conversationId === id) {
                        setConversationId(null)
                        setMessages([createInitialMessage()])
                      }
                    } catch {
                      showErrorToast('Failed to delete conversation')
                    }
                  }}
                />
              </div>
            )}
          </div>
        )}
        <div className="flex-1 h-full">
          <div className="flex flex-col h-full min-h-0" style={{ height: height ?? '100%' }}>
            {/* Header */}
            <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-2 mb-2">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-primary-100 dark:bg-primary-900/40 rounded-lg">
                  <MessageCircle className="icon-sm text-primary-600 dark:text-primary-400" aria-hidden="true" />
                </div>
                <div>
                  <h2 className="font-semibold text-gray-900 dark:text-gray-100 text-sm-fluid sm:text-base-fluid">
                    AI Financial Assistant
                  </h2>
                  <p className="text-xs-fluid text-gray-500 dark:text-gray-400">{headerSubtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleNewChat}
                  className="px-3 py-1.5 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-lg text-xs-fluid sm:text-sm-fluid hover:bg-primary-100 dark:hover:bg-primary-800/40 transition-colors"
                  aria-label="Start new chat"
                  title="New chat"
                >
                  <PlusSquare className="icon-sm mr-2 inline-block" aria-hidden="true" />
                  New chat
                </button>

                <button
                  type="button"
                  onClick={() => setSidebarVisible((v) => {
                    const nv = !v
                    // Save preference server-side
                    try {
                      fetch('/api/v1/chat/prefs', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sidebar: nv }) })
                    } catch {}
                    return nv
                  })}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  aria-label="Toggle conversations"
                  title="Toggle conversations"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M3 12h18M3 18h18" /></svg>
                </button>

                <button
                  type="button"
                  onClick={handleClearChat}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  aria-label="Clear chat"
                  title="Clear chat"
                >
                  <RotateCcw className="icon-sm text-gray-500" aria-hidden="true" />
                </button>
              </div>
            </div>

            {/* Messages (scrollable area only) */}
            <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-1" role="log" aria-label="Chat messages" aria-live="polite">
              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] sm:max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                        msg.type === 'user'
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                      }`}
                    >
                      {/* Render paragraphs for long bot replies */}
                      {msg.type === 'bot' ? (
                        renderMarkdown(msg.text)
                      ) : (
                        <p className="whitespace-pre-wrap break-words">{msg.text}</p>
                      )}
                      <p className={`text-xs mt-1 ${msg.type === 'user' ? 'text-primary-200' : 'text-gray-400 dark:text-gray-500'}`}>
                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Loading Indicator */}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex justify-start"
                >
                  <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-3">
                    <div className="flex gap-1.5">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Error */}
            {error && (
              <div
                className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-700 dark:text-red-400"
                role="alert"
              >
                {error}
              </div>
            )}

            {/* Feature Suggestions */}
            {showFeatures && messages.length <= 1 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {FEATURE_SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="px-3 py-1.5 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full text-xs-fluid sm:text-sm-fluid hover:bg-primary-100 dark:hover:bg-primary-800/40 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <form onSubmit={(e) => void handleSendMessage(e)} className="mt-3 flex gap-2">
              <label htmlFor="chat-input" className="sr-only">
                Type your message
              </label>
              <input
                ref={inputRef}
                id="chat-input"
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask me anything about finance..."
                disabled={isLoading}
                className="flex-1 rounded-lg border-2 border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 input-fluid px-3 py-2.5 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 transition-colors disabled:opacity-50"
                autoComplete="off"
              />
              <button
                type="submit"
                disabled={isLoading || !inputValue.trim()}
                className="px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                aria-label="Send message"
              >
                <Send className="icon-sm" aria-hidden="true" />
              </button>
            </form>
          </div>
        </div>
        </Card>
      </div>
   )
})

export default ChatComponent
