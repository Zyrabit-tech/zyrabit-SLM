# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY zyrabit-slm/web-ui/package.json ./
# Using npm as no pnpm is guaranteed in container unless installed
RUN npm install

# Copy source and build
COPY zyrabit-slm/web-ui .
RUN npm run build

# Production stage
FROM nginx:stable-alpine

# Copy build artifacts from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY zyrabit-slm/web-ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
