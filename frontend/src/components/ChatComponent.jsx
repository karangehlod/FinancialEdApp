import React, { useState, useRef, useEffect } from 'react'
import { Card } from './UI'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, MessageCircle, RotateCcw } from 'lucide-react'
import { showErrorToast, showSuccessToast } from '../utils/toast'
import { chatService } from '../services/chatService'

/**
 * Reusable Chat Component
 * Used by both ChatPage and DashboardPage to eliminate code duplication
 */
export const ChatComponent = ({ 
  className = '',
  height = 'h-[500px] sm:h-[600px]',
  showFeatures = false,
  headerSubtitle = 'Always here to help 💬'
}) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      text: 'Hello! 👋 I\'m your Financial Education Assistant. I\'m here to help you with budgeting tips, financial advice, and answering questions about your finances. How can I help you today?',
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Initialize conversation on mount
  useEffect(() => {
    const initConversation = async () => {
      try {
        const conversation = await chatService.createConversation()
        setConversationId(conversation.id)
      } catch (err) {
        console.error('Failed to create conversation:', err)
        // Use temporary conversation ID as fallback
        setConversationId(`temp-${Date.now()}`)
      }
    }
    initConversation()
  }, [])

  const handleSendMessage = async (e) => {
    e.preventDefault()
    
    if (!inputValue.trim()) {
      return
    }

    // Add user message immediately
    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      text: inputValue,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setError(null)

    try {
      // Call ChatService to send message
      const response = await chatService.sendMessage(userMessage.text, conversationId)
      
      const botMessage = {
        id: messages.length + 2,
        type: 'bot',
        text: response.reply,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, botMessage])
      
      // Update conversation ID if provided
      if (response.conversation_id && response.conversation_id !== conversationId) {
        setConversationId(response.conversation_id)
      }
    } catch (err) {
      console.error('Failed to send message:', err)
      setError('Failed to get response. Please try again.')
      showErrorToast('Failed to send message')
      
      // Remove the user message on error
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id))
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearChat = () => {
    setMessages([
      {
        id: 1,
        type: 'bot',
        text: 'Hello! 👋 I\'m your Financial Education Assistant. I\'m here to help you with budgeting tips, financial advice, and answering questions about your finances. How can I help you today?',
        timestamp: new Date(),
      },
    ])
    setError(null)
    showSuccessToast('Chat cleared!')
  }

  return (
    <div className={className}>
      <Card className={`flex flex-col ${height} overflow-hidden`}>
        {/* Chat Header */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 text-white p-4 sm:p-6 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="bg-white/20 p-2 sm:p-3 rounded-lg">
              <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-semibold">Financial Assistant</h2>
              <p className="text-xs sm:text-sm text-white/80">{headerSubtitle}</p>
            </div>
          </div>
          <button
            onClick={handleClearChat}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="Clear chat"
          >
            <RotateCcw className="w-4 h-4 sm:w-5 sm:h-5" />
          </button>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 space-y-3 sm:space-y-4 bg-gray-50 dark:bg-gray-900">
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs sm:max-w-sm md:max-w-md px-3 sm:px-4 py-2 sm:py-3 rounded-lg text-sm sm:text-base ${
                    message.type === 'user'
                      ? 'bg-primary-600 text-white rounded-br-none'
                      : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-bl-none shadow-sm'
                  }`}
                >
                  <p className="break-words">{message.text}</p>
                  <p className={`text-xs mt-1 ${message.type === 'user' ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'}`}>
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-4 py-3 rounded-lg rounded-bl-none border border-gray-200 dark:border-gray-700">
                <div className="flex gap-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 sm:p-4 flex-shrink-0">
          <form onSubmit={handleSendMessage} className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask me anything about finances..."
              className="flex-1 px-3 sm:px-4 py-2 sm:py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm sm:text-base bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              className="bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 dark:disabled:bg-gray-600 text-white p-2 sm:p-3 rounded-lg transition-colors flex items-center gap-2"
              title="Send message"
            >
              <Send className="w-4 h-4 sm:w-5 sm:h-5" />
              <span className="hidden sm:inline text-sm">Send</span>
            </button>
          </form>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-2">
            💡 Tip: Ask about budgeting, savings goals, debt management, or financial tips!
          </p>
        </div>
      </Card>

      {/* Features Info - only show if requested */}
      {showFeatures && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 mt-6 sm:mt-8">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white dark:bg-gray-800 p-4 sm:p-6 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <div className="flex items-start gap-3">
              <div className="bg-blue-100 dark:bg-blue-900/40 p-2 rounded-lg">
                <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="text-sm sm:text-base font-semibold text-gray-900 dark:text-gray-100">24/7 Support</h3>
                <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">Get help anytime you need it</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white dark:bg-gray-800 p-4 sm:p-6 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <div className="flex items-start gap-3">
              <div className="bg-green-100 dark:bg-green-900/40 p-2 rounded-lg">
                <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h3 className="text-sm sm:text-base font-semibold text-gray-900 dark:text-gray-100">Smart Tips</h3>
                <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">Get personalized financial advice</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white dark:bg-gray-800 p-4 sm:p-6 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <div className="flex items-start gap-3">
              <div className="bg-purple-100 dark:bg-purple-900/40 p-2 rounded-lg">
                <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <h3 className="text-sm sm:text-base font-semibold text-gray-900 dark:text-gray-100">Private Chat</h3>
                <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">Your conversations are secure</p>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
