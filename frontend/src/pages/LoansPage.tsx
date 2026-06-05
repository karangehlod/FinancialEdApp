import React from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { Card } from '../components/UI'

export const LoansPage: React.FC = () => (
  <Layout>
    <PageContainer title="Loans">
      <Card className="p-6 bg-white dark:bg-gray-800">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Loans</h3>
        <p className="text-sm-fluid text-gray-600 dark:text-gray-400 mt-2">Manage loans and EMIs. Content migrated to TypeScript.</p>
      </Card>
    </PageContainer>
  </Layout>
)
