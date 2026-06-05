# FinancialEdApp — Frontend

This document describes the frontend application for FinancialEdApp. It covers features, architecture, how things work, how to run locally and in Docker, build and deployment steps, scaling guidance, testing, and contribution notes.

Table of contents
- Project summary
- Key features
- Tech stack
- Repo layout
- How it works (high level)
- Running locally
- Building for production
- Docker and deployment
- Integrating with the backend
- Testing
- Accessibility and responsiveness
- Scaling & performance guidance
- Contribution guide
- Interview guide / talking points

Project summary
---------------
The frontend is a single-page application (SPA) built with modern frontend tooling. It provides user interface for account management, dashboards, budgets, goals, transaction views and the conversational advisor interface that interacts with the backend agent.

Key features
------------
- Responsive UI for dashboards, budgets, goals and transaction history
- Conversation UI for asking the financial advisor (LangChain-backed) questions
- Authentication flows (login, logout, password reset)
- Client-side input validation and optimistic UI patterns for responsiveness
- Build scripts for creating production bundles

Tech stack
----------
- Framework: Vite + React (or the chosen framework in the codebase)
- Styling: TailwindCSS (configured in tailwind.config.js)
- TypeScript configuration available (tsconfig.json)
- Node.js / npm or yarn for package management

Repo layout
----------
- src/: application source
  - components/: reusable UI components
  - pages/: route-level components
  - services/: API clients and app-level services
  - hooks/: custom React hooks
  - styles/: global styles and Tailwind config
- index.html / main.tsx: SPA entrypoint
- build.sh: convenience script for building
- Dockerfile: container image definition
- setup.sh: local setup helper

How it works (high level)
-------------------------
- Single Page Application served as static assets (HTML/CSS/JS)
- On login, the frontend obtains an auth token (or sets a session cookie) and uses it for API requests
- Conversation UI sends user messages to the backend agent endpoint and displays streaming or final responses
- State management is local (React context or other chosen state manager); ephemeral UI state is not stored on the backend unless user explicitly saves data

Running locally
---------------
Prerequisites
- Node.js >= 18, npm/yarn
- Backend running locally (see backend README) or a configured API endpoint

Steps
1. Install dependencies
   - npm install
2. Start dev server
   - npm run dev
   - By default Vite serves at http://localhost:5173 (configurable)
3. Open browser and visit the dev URL

Environment variables
- Use .env or .env.local for API_BASE_URL and feature flags

Building for production
-----------------------
1. Build
   - npm run build
   - Output is created under the `dist/` folder
2. Preview
   - npm run preview (serves the production build locally)

Docker and deployment
---------------------
- Build production image
  - docker build -t financialed-frontend:latest -f frontend/Dockerfile .
- Serve with a static web server (nginx) in production container
- For static web hosting, upload `dist/` to S3, Azure Static Web Apps, or similar

Integrating with the backend
----------------------------
- API_BASE_URL must point to the backend endpoint
- If using cookies for auth, ensure same-site and secure cookie configuration match your deployment
- For local dev, use proxy (vite config) to forward API requests to backend host/port

Testing
-------
- Unit tests: use your chosen test runner (Vitest/Jest) and run npm test
- E2E tests: Cypress / Playwright for flows like authentication and advisor conversation

Accessibility and responsiveness
--------------------------------
- Use semantic HTML and proper ARIA attributes on interactive components
- Ensure keyboard navigability across the conversation UI and forms
- Test across mobile breakpoints and use responsive design best practices (Tailwind utility classes)

Performance and scaling guidance
--------------------------------
- Keep client bundles small: split code by route and lazy-load heavy components
- Use HTTP caching and long-lived cache headers for static assets
- Use a CDN for distribution of static assets for low latency worldwide
- Server-Side Rendering (SSR) or edge rendering can be considered if SEO or initial load is critical

Security considerations
- Sanitize and validate user input
- Do not store secrets or API keys in client code
- Use HTTPS in production
- Use Content Security Policy (CSP) to reduce XSS risks

Contribution guide
------------------
- Follow UI component patterns and the existing folder structure
- Ensure unit tests for new components and pages
- Run `npm test` and `npm run lint` before opening a PR
- Keep UI changes backwards compatible where possible

Interview guide / talking points
-------------------------------
When explaining the frontend, cover:
- Chosen framework, build tooling and rationale (Vite for fast dev)
- How the conversation UI integrates with the backend agent (streaming vs final responses)
- Performance strategies (code-splitting, caching, CDN)
- How to add a new page: create route, page component, API service call, and wire tests

Appendix
--------
- Scripts: build.sh, setup.sh, test-integration.js
- Useful files: index.html, tailwind.config.js, vite.config.js, tsconfig.json


Maintainers
- Primary: project maintainers (see CODEOWNERS or repository settings)

License
- See top-level LICENSE file (if present)

Contact
- For questions, open an issue or reach out to maintainers via repository channels.
