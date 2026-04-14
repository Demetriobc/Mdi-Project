# Build estático (VITE_* embutidas no JS nesta fase)
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=
ARG VITE_USD_BRL_RATE=5.5
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_USD_BRL_RATE=$VITE_USD_BRL_RATE

RUN npm run build \
    && test -f dist/index.html || (echo "ERRO: dist/index.html em falta" && exit 1)

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /tmp/default.conf.tpl
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
    && rm -f /etc/nginx/conf.d/default.conf

ENV PORT=8080
EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
