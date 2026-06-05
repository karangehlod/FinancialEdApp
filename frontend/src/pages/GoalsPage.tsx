import React from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { Card } from '../components/UI'

export const GoalsPage: React.FC = () => (
  <Layout>
    <PageContainer title="Goals">
      <Card className="p-6 bg-white dark:bg-gray-800">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Goals</h3>
        <p className="text-sm-fluid text-gray-600 dark:text-gray-400 mt-2">Track progress towards your financial goals. Content migrated to TypeScript.</p>
      </Card>
    </PageContainer>
  </Layout>
)
