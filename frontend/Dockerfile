# Build estático — VITE_* embutidas no JS aqui
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
    && test -f dist/index.html || (echo "dist/index.html nao encontrado" && exit 1)

# Runtime: nginx serve o dist/
FROM nginx:1.27-alpine

# O entrypoint oficial do nginx faz envsubst em /etc/nginx/templates/*.template
# e substitui TODAS as variáveis de ambiente — incluindo PORT injetada pela Railway.
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

RUN rm -f /etc/nginx/conf.d/default.conf \
    # Railway pode ter muitos CPUs visíveis → limita workers para não dar OOM
    && sed -i 's/^worker_processes.*/worker_processes 2;/' /etc/nginx/nginx.conf

ENV PORT=8080
EXPOSE 8080
