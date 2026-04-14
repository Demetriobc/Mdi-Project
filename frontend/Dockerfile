# Build estático (VITE_* embutidas no JS nesta fase)
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Obrigatório no deploy: URL pública da API FastAPI (ex. https://xxx.up.railway.app)
ARG VITE_API_BASE_URL=
ARG VITE_USD_BRL_RATE=5.5
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_USD_BRL_RATE=$VITE_USD_BRL_RATE

RUN npm run build

# Servir SPA (fallback para React Router se um dia usares)
FROM node:22-alpine AS runtime

WORKDIR /app
RUN npm install -g serve@14

COPY --from=build /app/dist ./dist

ENV PORT=3000
EXPOSE 3000

CMD ["sh", "-c", "serve -s dist -l tcp://0.0.0.0:${PORT:-3000}"]
