/**
 * Chat service — typed API layer for AI chat functionality.
 * Falls back to dummy responses when the backend is unavailable.
 */

import apiClient from './api'
import logger from '@/utils/logger'

// ── Types ──────────────────────────────────────────────────────────────

export interface ChatMessage {
  readonly reply: string
  readonly conversation_id: string | null
}

export interface ChatConversation {
  readonly id: string
  readonly title?: string | null
  readonly last?: string | null
  readonly ts?: string | null
}

interface ChatHistory {
  readonly messages: readonly ChatMessage[]
}

interface ChatConversationList {
  readonly conversations: readonly ChatConversation[]
}

// ── Dummy Responses ────────────────────────────────────────────────────

const DUMMY_RESPONSES: readonly string[] = [
  "That's a great question! Let me help you with that. Based on your current spending patterns, I'd recommend focusing on budgeting for essentials first.",
  'I understand your concern. Building a strong financial foundation starts with tracking your expenses and setting realistic goals.',
  "You're on the right track! Creating a budget is an important first step towards financial stability.",
  "Here's a tip: Try the 50/30/20 rule — allocate 50% to needs, 30% to wants, and 20% to savings.",
  "It's great that you're thinking about your financial future! Do you have any specific goals in mind?",
  'Managing debt is important. Would you like tips on how to reduce your debt effectively?',
  'Smart investing starts with understanding your risk tolerance and financial goals.',
  'Emergency funds are crucial! A good rule of thumb is to save 3–6 months of living expenses.',
  'Good financial habits take time to develop. Start small and build from there!',
  'Would you like to set a budget for a specific category of expenses?',
] as const

function getRandomDummyResponse(): string {
  return DUMMY_RESPONSES[Math.floor(Math.random() * DUMMY_RESPONSES.length)] ?? DUMMY_RESPONSES[0]!
}

// ── Service ────────────────────────────────────────────────────────────

export const chatService = {
  async sendMessage(
    message: string,
    conversationId: string | null = null
  ): Promise<ChatMessage> {
    try {
      const payload: Record<string, unknown> = {
        message,
        conversation_id: conversationId,
      }

      const response = await apiClient.post<ChatMessage>('/chat/message', payload)
      return response.data
    } catch {
      logger.warn('Chat API not available, using fallback response')
      return {
        reply: getRandomDummyResponse(),
        conversation_id: conversationId,
      }
    }
  },

  async getHistory(conversationId: string): Promise<ChatHistory> {
    try {
      const response = await apiClient.get<ChatHistory>(`/chat/history/${conversationId}`)
      return response.data
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 403) throw err
      logger.warn('Failed to fetch chat history')
      return { messages: [] }
    }
  },

  async createConversation(): Promise<ChatConversation> {
    try {
      const response = await apiClient.post<ChatConversation>('/chat/conversation', {})
      return response.data
    } catch {
      logger.warn('Failed to create conversation')
      return { id: `temp-${Date.now()}` }
    }
  },

  async getConversations(): Promise<ChatConversationList> {
    try {
      const response = await apiClient.get<ChatConversationList>(`/chat/conversations`)
      return response.data
    } catch {
      logger.warn('Failed to fetch conversations')
      return { conversations: [] }
    }
  },

  async deleteConversation(conversationId: string): Promise<void> {
    try {
      await apiClient.delete(`/chat/conversation/${conversationId}`)
    } catch (err) {
      logger.warn(`Failed to delete conversation ${conversationId}`)
      throw err
    }
  },

  async migrateConversation(payload: { messages: { role: string; content: string; timestamp?: string }[] }) {
    try {
      const response = await apiClient.post<ChatConversation>('/chat/migrate', payload)
      return response.data
    } catch (err) {
      logger.warn('Failed to migrate local conversation to server')
      throw err
    }
  },
} as const

export default chatService
