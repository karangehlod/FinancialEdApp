/**
 * Component Barrel Exports
 * Centralized exports for easier imports
 */

// UI Components
export {
  LoadingSpinner,
  Card,
  Button,
  Input,
  Select,
  Badge,
  Modal,
  Alert,
  StatCard,
  EmptyState,
  ProgressBar,
} from './UI'

// Layout Components
export { Sidebar, Header, Layout, PageContainer, Tabs } from './Layout'

// Footer (public pages — contact, features, legal)
export { Footer } from './Footer'

// Route Protection
export { ProtectedRoute } from './ProtectedRoute'
