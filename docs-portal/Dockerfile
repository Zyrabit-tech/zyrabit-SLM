FROM node:latest-slim

WORKDIR /site
COPY package.json ./
RUN corepack enable \
    && if ! command -v pnpm >/dev/null 2>&1; then corepack prepare pnpm@latest --activate; fi \
    && if ! command -v pnpm >/dev/null 2>&1; then echo "ERROR: no se encontro el paquete pnpm" >&2; exit 1; fi \
    && pnpm install --no-frozen-lockfile

COPY . .
EXPOSE 3001
CMD ["pnpm", "start"]
