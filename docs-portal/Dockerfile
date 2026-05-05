FROM node:20-alpine AS builder

WORKDIR /site
COPY package.json pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY . .
RUN pnpm run build

# Stage 2: Runtime
FROM node:20-alpine

WORKDIR /site
COPY --from=builder /site ./

EXPOSE 3001
USER node
CMD ["pnpm", "start"]
