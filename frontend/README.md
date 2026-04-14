# Interface React (Vite)

Consome a API FastAPI (`/predict`, `/chat`, `/health`). Em **dev**, o proxy do Vite manda `/api` para `localhost:8001`. Em **produção**, a URL da API vem de `VITE_API_BASE_URL` (incorporada no build).

## Desenvolvimento local

```bash
npm ci
npm run dev
```

Garante a API em `http://localhost:8001` (ou ajusta `vite.config.ts`).

## Deploy na Railway (segundo serviço)

1. No mesmo projeto Railway onde está a API: **New** → **GitHub Repo** (o mesmo repositório) ou **Empty service** → liga ao repo.
2. **Settings** do novo serviço:
   - **Root Directory:** `frontend`
   - **Dockerfile path:** `Dockerfile` (default se estiver em `frontend/`)
3. **Variables** (marca **Available at Build Time** nas que forem `VITE_*`):
   - `VITE_API_BASE_URL` = `https://mdi-project-production.up.railway.app` (substitui pelo domínio real da tua API)
   - Opcional: `VITE_USD_BRL_RATE` = `5.5`
4. **Generate Domain** no serviço do front — é o link para partilhar com recrutadores.
5. Na **API** (serviço antigo), adiciona o domínio do React a `CORS_ORIGINS` se usares `APP_ENV=production`, por exemplo:
   - `CORS_ORIGINS=https://teu-frontend-production.up.railway.app`
   - Em `staging` / `development` a API já aceita `*` e não precisas disto.

Build local da imagem (a partir da raiz do repo):

```bash
docker build -f frontend/Dockerfile ./frontend -t house-ui \
  --build-arg VITE_API_BASE_URL=https://SUA-API.up.railway.app
```

## Scripts

| Comando | Descrição |
|---------|-----------|
| `npm run dev` | Servidor de desenvolvimento |
| `npm run build` | Typecheck + bundle para `dist/` |
| `npm run preview` | Pré-visualizar o `dist/` |
