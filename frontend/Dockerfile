# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Accept build-time environment variables for Vite
ARG VITE_API_URL
ARG VITE_APP_NAME
ARG VITE_APP_VERSION

ENV VITE_API_URL=$VITE_API_URL \
    VITE_APP_NAME=$VITE_APP_NAME \
    VITE_APP_VERSION=$VITE_APP_VERSION

COPY package*.json ./
RUN npm install --legacy-peer-deps

COPY . .
RUN npm run build

# Stage 2: Serve with nginx (no Node.js runtime needed — just static files)
FROM nginx:alpine AS runtime

RUN apk add --no-cache curl

# Copy the built app
COPY --from=builder /app/dist /usr/share/nginx/html

# SPA routing config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -sf http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
