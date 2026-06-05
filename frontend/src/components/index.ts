/**
 * Component Barrel Exports — centralised for cleaner imports.
 */

// UI Primitives
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
  FluidIcon,
  type IconComponent,
} from './UI'

// Layout
export { Sidebar, Header, Layout, PageContainer } from './Layout'

// Error Boundary
export { ErrorBoundary } from './ErrorBoundary'

// Route Protection
export { ProtectedRoute } from './ProtectedRoute'

// Session Warning
export { SessionWarning } from './SessionWarning'

// OAuth Buttons
export { OAuthButtons } from './OAuthButtons'

// Footer
export { Footer } from './Footer'

// Chat
export { ChatComponent } from './ChatComponent'

// Fluid primitives
export { FluidContainer } from './FluidContainer'
export { FluidGrid } from './FluidGrid'
export { StatCard as StatCardCompact } from './StatCard'
