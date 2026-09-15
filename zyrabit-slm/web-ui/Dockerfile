# Build stage
FROM node:22-alpine AS build

WORKDIR /app

# Install pnpm explicitly with fixed stable version
RUN apk add --no-cache libc6-compat
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="${PNPM_HOME}:${PATH}"
RUN npm install -g pnpm@10.34.5 && npm cache clean --force

COPY zyrabit-slm/web-ui/package.json zyrabit-slm/web-ui/pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# Copy source and build
COPY zyrabit-slm/web-ui .
RUN pnpm run build

# Production stage
FROM nginx:stable-alpine

# Copy build artifacts from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY zyrabit-slm/web-ui/nginx.conf /etc/nginx/conf.d/default.conf
COPY zyrabit-slm/web-ui/docker-entrypoint.sh /docker-entrypoint.d/40-zyrabit-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-zyrabit-runtime-config.sh

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
