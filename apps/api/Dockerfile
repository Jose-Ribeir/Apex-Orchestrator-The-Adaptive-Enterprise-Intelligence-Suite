# Build from repo root: docker build -f apps/api/Dockerfile .
FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@9.0.0 --activate
WORKDIR /app

# Deps only: cache layer until lockfile or api deps change
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/api/package.json ./apps/api/
COPY packages/typescript-config/package.json ./packages/typescript-config/
COPY packages/eslint-config/package.json ./packages/eslint-config/
RUN pnpm install --frozen-lockfile

# Build: no install, reuse deps
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/api/node_modules ./apps/api/node_modules
COPY . .
RUN pnpm --filter @ai-router/api build

# Runner: minimal copy, no packages (api has no runtime workspace deps)
FROM base AS runner
ARG PORT=4000
ENV NODE_ENV=production
ENV PORT=${PORT}
WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY apps/api/package.json apps/api/tsconfig.json ./apps/api/
COPY --from=builder /app/apps/api/dist ./apps/api/dist
COPY apps/api/config ./apps/api/config
COPY apps/api/db ./apps/api/db
COPY apps/api/.sequelizerc ./apps/api/
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/apps/api/node_modules ./apps/api/node_modules
USER node
EXPOSE ${PORT}
WORKDIR /app/apps/api
CMD ["sh", "-c", "npx sequelize-cli db:migrate && node dist/index.js"]
