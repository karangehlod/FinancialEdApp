# Financial Education App - Frontend

A modern, interactive React frontend for the Financial Education Application. Built with React 18, Tailwind CSS, Framer Motion, and Zustand for state management.

## 🎯 Features

- **Authentication**: Secure login/registration with JWT tokens
- **Dashboard**: Overview of financial metrics and quick access cards
- **Expenses Management**: Track and categorize expenses with filters
- **Budget Planning**: Set spending limits and monitor alerts
- **Financial Goals**: Set and track savings goals with progress tracking
- **Loan Management**: Track loans with interest rates and terms
- **Responsive Design**: Mobile-first, fully responsive UI
- **Modern Animations**: Smooth transitions and interactive elements
- **Real-time Updates**: State management with Zustand

## 🚀 Getting Started

### Prerequisites

- Node.js 16+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Installation

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env.local
   ```
   
   Edit `.env.local`:
   ```env
   VITE_API_URL=http://localhost:8000
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── UI.jsx          # Core components (Card, Button, Input, etc.)
│   ├── Layout.jsx      # Navigation and layout components
│   └── ProtectedRoute.jsx
├── pages/              # Page components
│   ├── LoginPage.jsx
│   ├── RegisterPage.jsx
│   ├── DashboardPage.jsx
│   ├── ExpensesPage.jsx
│   ├── BudgetsPage.jsx
│   ├── GoalsPage.jsx
│   └── LoansPage.jsx
├── hooks/              # Custom React hooks
│   └── useAuth.js     # Authentication hooks
├── services/           # API services
│   ├── api.js         # Axios instance with interceptors
│   └── apiService.js  # API endpoint wrappers
├── store/              # State management (Zustand)
│   ├── authStore.js
│   └── index.js       # Feature stores
├── utils/              # Utility functions
│   ├── helpers.js     # Format and calculation helpers
│   └── toast.js       # Toast notification utilities
├── App.jsx            # Main app with routing
├── main.jsx           # Entry point
└── index.css          # Global styles
```

## 🎨 Theme & Design

- **Color Palette**: Blue-based modern theme with gradients
- **Typography**: System font stack for optimal rendering
- **Animations**: Framer Motion for smooth transitions
- **Component Library**: Custom component system following SOLID principles

## 🔐 Authentication Flow

1. User registers or logs in
2. Backend returns `access_token` and `refresh_token`
3. Tokens stored in localStorage
4. API interceptor adds token to all requests
5. On token expiry, automatic refresh is attempted
6. Failed refresh redirects to login

## 📊 State Management

Using Zustand for simplified, centralized state:

- **authStore**: User authentication state
- **expenseStore**: Expense data and operations
- **budgetStore**: Budget data and operations
- **goalStore**: Financial goal data and operations
- **loanStore**: Loan data and operations
- **notificationStore**: User notifications

## 🔌 API Integration

All API calls through `apiService.js`:
- Centralized error handling
- Token management
- Request/response interceptors
- Type-safe data structures

## 🎯 Key Components

### UI Components
- `Card`: Glassomorphism container
- `Button`: Multi-variant button with states
- `Input` & `Select`: Form controls with validation
- `Modal`: Reusable dialog component
- `StatCard`: Statistic display cards
- `ProgressBar`: Visual progress indicator

### Layout Components
- `Sidebar`: Navigation with responsive behavior
- `Header`: Top navigation with notifications
- `Layout`: Main layout wrapper
- `PageContainer`: Page header and content wrapper

## 🚢 Building for Production

```bash
npm run build
```

Output goes to `dist/` folder. Can be served by any static server.

## 📝 Development Guidelines

### Code Structure
- Components are functional React components
- Props validation through JSDoc
- Consistent error handling
- Accessibility-first approach

### Styling
- Tailwind CSS for styling
- Custom utility classes for common patterns
- Responsive design with mobile-first approach

### API Communication
- Use store actions for data fetching
- Handle loading and error states
- Show user feedback with toast notifications

## 🔄 Routing

- `/login` - Public login page
- `/register` - Public registration page
- `/dashboard` - Protected dashboard
- `/expenses` - Protected expenses management
- `/budgets` - Protected budget planning
- `/goals` - Protected financial goals
- `/loans` - Protected loan tracking

All protected routes require authentication.

## 📱 Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## 🐛 Troubleshooting

### API Connection Issues
- Ensure backend is running on `http://localhost:8000`
- Check `VITE_API_URL` in `.env.local`
- Verify CORS is properly configured on backend

### Authentication Issues
- Clear localStorage if tokens are invalid
- Check browser console for error messages
- Verify backend token endpoints

### Build Issues
- Delete `node_modules` and `dist`
- Run `npm install` again
- Check Node.js version (16+)

## 📚 Dependencies

- **react**: UI library
- **react-router-dom**: Client-side routing
- **axios**: HTTP client
- **zustand**: State management
- **framer-motion**: Animation library
- **lucide-react**: Icon library
- **react-hot-toast**: Toast notifications
- **tailwindcss**: CSS framework

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

1. Follow the code structure
2. Use meaningful component and variable names
3. Add JSDoc comments for complex functions
4. Test on mobile devices
5. Maintain responsive design

## 📞 Support

For issues or questions, please open an issue in the repository.
