# Build from repo root: docker build -f apps/api/Dockerfile .
FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/api/package.json ./apps/api/
COPY packages/typescript-config/package.json ./packages/typescript-config/
RUN pnpm install --frozen-lockfile

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/api/node_modules ./apps/api/node_modules
COPY --from=deps /app/packages ./packages
COPY . .
RUN pnpm install
RUN pnpm --filter @ai-router/api build

FROM base AS runner
ARG PORT=4000
ENV NODE_ENV=production
ENV PORT=${PORT}
WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY apps/api/package.json apps/api/tsconfig.json ./apps/api/
COPY apps/api/dist ./apps/api/dist
COPY apps/api/config ./apps/api/config
COPY apps/api/db ./apps/api/db
COPY apps/api/.sequelizerc ./apps/api/
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/apps/api/node_modules ./apps/api/node_modules
COPY --from=builder /app/packages ./packages
USER node
EXPOSE ${PORT}
WORKDIR /app/apps/api
CMD ["sh", "-c", "npx sequelize-cli db:migrate && node dist/index.js"]
