# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Install pnpm and dependencies
RUN apk add --no-cache libc6-compat
RUN npm install -g pnpm && npm cache clean --force
COPY zyrabit-slm/web-ui/package.json zyrabit-slm/web-ui/pnpm-lock.yaml* ./
RUN pnpm install

# Copy source and build
COPY zyrabit-slm/web-ui .
RUN pnpm run build

# Production stage
FROM nginx:stable-alpine

# Copy build artifacts from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY zyrabit-slm/web-ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
