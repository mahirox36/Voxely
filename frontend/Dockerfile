# Stage 1: Build
FROM node:20 AS builder
WORKDIR /app

# Copy package files first for caching
COPY package*.json ./
RUN npm install --frozen-lockfile

# Copy all source code
COPY . .

# Build the Next.js app for production
RUN npm run build

# Stage 2: Run
FROM node:20-slim
WORKDIR /app

# Copy node_modules and build output from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json

# Expose the default Next.js port
EXPOSE 3000

# Start the Next.js server in production mode
CMD ["npm", "run", "start"]
