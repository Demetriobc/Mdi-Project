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
    && test -f dist/index.html || (echo "ERRO: dist/index.html ausente" && exit 1)

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
# Config estática — sem substituição de variáveis em runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN sed -i 's/^worker_processes.*/worker_processes 2;/' /etc/nginx/nginx.conf

EXPOSE 8080
