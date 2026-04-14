/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USD_BRL_RATE?: string
  /** URL absoluta da API FastAPI (ex.: https://mdi-project-production.up.railway.app) */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
