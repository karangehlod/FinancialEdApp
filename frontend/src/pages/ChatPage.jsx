import React from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { useProtectedRoute } from '../hooks/useAuth'
import { LoadingSpinner } from '../components/UI'
import { ChatComponent } from '../components/ChatComponent'

export const ChatPage = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-screen">
          <LoadingSpinner />
        </div>
      </Layout>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <Layout>
      <PageContainer
        title="Financial Chat Assistant"
        subtitle="Get instant help with your financial questions"
      >
        <ChatComponent 
          height="h-[600px]"
          showFeatures={true}
        />
      </PageContainer>
    </Layout>
  )
}
