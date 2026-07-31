# Build stage
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Production stage
FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY --from=build /app/src ./src

# Security Hardening: Run as non-root node user
USER node

EXPOSE 5000
ENV NODE_ENV=production

CMD ["node", "src/index.js"]
