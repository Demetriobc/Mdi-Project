/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USD_BRL_RATE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
