# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Accept build-time environment variables for Vite
ARG VITE_API_URL
ARG VITE_APP_NAME
ARG VITE_APP_VERSION
ARG VITE_ADMIN_EMAILS

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_APP_NAME=$VITE_APP_NAME
ENV VITE_APP_VERSION=$VITE_APP_VERSION
ENV VITE_ADMIN_EMAILS=$VITE_ADMIN_EMAILS

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the React app
RUN npm run build

# Production/Development stage
FROM node:18-alpine

WORKDIR /app

# Install serve to run the production build and wget for healthcheck
RUN npm install -g serve

# Copy built app from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./

# Install production dependencies only
RUN npm ci --production

# Expose port
EXPOSE 3000

# Set environment to production
ENV NODE_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Start the app
CMD ["serve", "-s", "dist", "-l", "3000"]
