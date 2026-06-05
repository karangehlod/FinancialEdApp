import React from 'react'
import { Layout } from '../components/Layout'
import { useProtectedRoute } from '../hooks/useAuth'
import { LoadingSpinner } from '../components/UI'
import { ChatComponent } from '../components/ChatComponent'

export const ChatPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()

  if (isLoading) {
    return (
      <Layout showHeader={false} noContainer={true}>
        <div className="flex items-center justify-center h-screen">
          <LoadingSpinner />
        </div>
      </Layout>
    )
  }

  if (!isAuthenticated) return null

  return (
    <Layout showHeader={false} noContainer={true}>
      <div className="w-full h-full flex">
        <ChatComponent showFeatures={true} showSidebar={true} />
      </div>
    </Layout>
  )
}

export default ChatPage
