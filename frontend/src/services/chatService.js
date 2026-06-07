import apiClient from './api'

export const chatService = {
  // Send a message to the chat API and get a response
  sendMessage: async (message, conversationId = null) => {
    try {
      const response = await apiClient.post('/chat/message', {
        message,
        conversation_id: conversationId,
      })
      return response.data
    } catch (error) {
      // If API not available, return dummy response
      console.warn('Chat API not available, using dummy response')
      return {
        reply: getDummyResponse(),
        conversation_id: conversationId,
      }
    }
  },

  // Get chat history
  getHistory: async (conversationId) => {
    try {
      const response = await apiClient.get(`/chat/history/${conversationId}`)
      return response.data
    } catch (error) {
      console.warn('Failed to fetch chat history')
      return { messages: [] }
    }
  },

  // Create a new conversation
  createConversation: async () => {
    try {
      const response = await apiClient.post('/chat/conversation', {})
      return response.data
    } catch (error) {
      console.warn('Failed to create conversation')
      return { id: `temp-${Date.now()}` }
    }
  },

  // Get all conversations
  getConversations: async () => {
    try {
      const response = await apiClient.get('/chat/conversations')
      return response.data
    } catch (error) {
      console.warn('Failed to fetch conversations')
      return { conversations: [] }
    }
  },
}

// Dummy responses for when backend is not available
const getDummyResponse = () => {
  const responses = [
    "That's a great question! Let me help you with that. Based on your current spending patterns, I'd recommend focusing on budgeting for essentials first.",
    "I understand your concern. Building a strong financial foundation starts with tracking your expenses and setting realistic goals.",
    "You're on the right track! Creating a budget is an important first step towards financial stability.",
    "Here's a tip: Try the 50/30/20 rule - allocate 50% to needs, 30% to wants, and 20% to savings.",
    "It's great that you're thinking about your financial future! Do you have any specific goals in mind?",
    "Managing debt is important. Would you like tips on how to reduce your debt effectively?",
    "Smart investing starts with understanding your risk tolerance and financial goals. Let me know if you'd like to discuss this further.",
    "Emergency funds are crucial! A good rule of thumb is to save 3-6 months of living expenses.",
    "Good financial habits take time to develop. Start small and build from there!",
    "Would you like to set a budget for a specific category of expenses?",
  ]
  return responses[Math.floor(Math.random() * responses.length)]
}

export default chatService
