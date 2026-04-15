# Estratégia de Deploy

---

## 1. Visão Geral

A solução em produção é composta por dois serviços independentes hospedados no Railway, conectados por uma API REST:

> **Diagrama interativo:** [`docs/diagrams/01-system-architecture.excalidraw`](diagrams/01-system-architecture.excalidraw)  
> Abra no VS Code com a extensão **Excalidraw** ou em [excalidraw.com](https://excalidraw.com) → Abrir arquivo.

![Arquitetura do sistema](diagrams/01-system-architecture.excalidraw)

Os dois serviços são deployados e escalados de forma independente. O frontend é um build estático servido por Nginx — não tem lógica de servidor além de roteamento. Toda a computação ocorre na API.

---

## 2. Componentes

### 2.1 Frontend (React + Vite + Nginx)

**Responsabilidade:** interface do usuário  
**stack:** React , TypeScript, Tailwind , shadcn 
**Diretório:** `frontend/`  
**Configuração Railway:** Root Directory = `frontend`, usa `frontend/Dockerfile`

O frontend é compilado em tempo de build com `npm run build`, gerando um bundle estático em `dist/`. O Nginx serve esses arquivos e faz proxy de roteamento para o `index.html` (SPA).

A URL da API é injetada em tempo de build via variável de ambiente:

```
VITE_API_BASE_URL=https://sua-api.up.railway.app
```

Esta variável **precisa estar marcada como "Available at Build Time"** no painel do Railway — diferente de variáveis de runtime, o Vite a incorpora diretamente no bundle JavaScript.

### 2.2 API (FastAPI + Uvicorn)

**Responsabilidade:** inferência ML, RAG, chat  
**Tecnologia:** Python 3.11, FastAPI, Uvicorn  
**Diretório:** raiz do repositório  
**Configuração Railway:** usa `Dockerfile` na raiz

A API expõe três endpoints principais:

| Rota | Método | Descrição |
|---|---|---|
| `/health` | GET | Status do serviço, disponibilidade de artefatos e banco |
| `/predict` | POST | Recebe características do imóvel, retorna previsão + intervalo |
| `/chat` | POST | Recebe pergunta + contexto do imóvel, retorna resposta do LLM |

O startup da API verifica automaticamente:
- Presença do modelo e preprocessador em `artifacts/model/`
- Presença do índice FAISS em `artifacts/vectorstore/`
- Conectividade com o banco de dados
- Configuração de chave LLM

Serviços não disponíveis (modelo ausente, banco offline, sem chave LLM) não travam o startup — a API sobe em modo degradado e reporta o estado via `/health`.

### 2.3 Modelo de ML (XGBoost + preprocessador)

O modelo não é carregado via API externa — está embutido na imagem Docker como arquivos `.joblib`:

- `artifacts/model/house_price_model.joblib` — pipeline completo (feature eng + preprocessador + XGBoost p50)
- `artifacts/model/preprocessor.joblib` — pipeline de pré-processamento isolado (usado para extrair matrix para SHAP)
- `artifacts/model/metadata.json` — metadados do treino (métricas, hiperparâmetros, importâncias, medianas por zipcode)

O carregamento é feito uma vez no startup e mantido em memória. A latência de inferência é < 100ms por requisição em condições normais.

### 2.4 Camada RAG

**Componentes:**
- `artifacts/vectorstore/index.faiss` — índice FAISS com embeddings da knowledge base
- `data/knowledge_base/` — documentos fonte (5 arquivos markdown + CSV)

O retriever busca os 4 trechos mais relevantes para cada pergunta e os injeta no prompt do LLM. Os embeddings são gerados localmente com `fastembed` (gratuito) ou via API da OpenAI, conforme configuração.

### 2.5 Banco de Dados (PostgreSQL)

**Uso:** persistência de logs de predição para análise posterior  
**Status:** opcional — a API funciona sem banco configurado

Quando disponível, cada chamada ao `/predict` é registrada com timestamp, features de entrada, previsão e intervalo. Esses logs são a base para monitoramento de drift e análise de uso em produção.

---

## 3. Fluxo de Inferência

**Fluxo `/predict`** — diagrama interativo:

> [`docs/diagrams/02-inference-flow.excalidraw`](diagrams/02-inference-flow.excalidraw)

![Fluxo de inferência](diagrams/02-inference-flow.excalidraw)

**Fluxo `/chat`:**

1. Usuário digita pergunta no chat
2. Frontend envia: pergunta + dados do imóvel + previsão atual
3. `POST /chat` → API
4. RAG retriever gera embedding da pergunta
5. Busca vetorial no FAISS → top-4 trechos relevantes
6. Prompt montado: contexto recuperado + dados do imóvel + previsão + pergunta
7. LLM (OpenAI GPT-4o-mini ou Groq Llama 3.1) gera resposta
8. API retorna resposta em texto
9. React exibe no painel de chat

---

## 4. Infraestrutura

### 4.1 Docker

**API (multi-stage build):**

O `Dockerfile` na raiz usa dois estágios:

1. **Stage builder:** instala dependências Python, baixa o dataset KC House (via script com fallback para mirrors), executa `python -m app.ml.train` (treino XGBoost) e `python -m app.rag.build_kb` (indexação FAISS)
2. **Stage final:** copia apenas código + artefatos gerados (sem dados brutos), resultado em imagem mais enxuta

O treino dentro do Docker garante que o modelo em produção foi treinado no mesmo ambiente que será executado — sem divergências de biblioteca ou versão.

**Build time:** 10–20 minutos na primeira execução (treino XGBoost + indexação FAISS). Railway tem timeout configurado para acomodar isso.

**Frontend:**

`frontend/Dockerfile` usa Node.js para build e Nginx para serving. O `nginx.conf` configura roteamento para SPA e proxy de cache para assets estáticos.

### 4.2 Railway

**Configuração do serviço API (`railway.toml` na raiz):**

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 120
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 5
```

O `healthcheckPath = "/health"` garante que o Railway só considera o serviço saudável após o startup completar com sucesso. O timeout de 120s acomoda o carregamento dos artefatos na memória.

**Configuração do serviço Frontend:**

- Root Directory: `frontend`
- Dockerfile: `frontend/Dockerfile`
- Build Arg: `VITE_API_BASE_URL` = URL pública da API (marcar como "Available at Build Time")

### 4.3 Variáveis de Ambiente

**API (runtime):**

| Variável | Descrição | Obrigatória |
|---|---|---|
| `APP_ENV` | `production` ou `development` | Sim |
| `LLM_PROVIDER` | `openai` ou `groq` | Sim |
| `OPENAI_API_KEY` | Chave OpenAI | Se provider = openai |
| `GROQ_API_KEY` | Chave Groq | Se provider = groq |
| `DATABASE_URL` | Connection string PostgreSQL | Não (logs desativados se ausente) |
| `CORS_ORIGINS` | URLs do frontend separadas por vírgula | Recomendado em produção |

**Frontend (build time):**

| Variável | Descrição |
|---|---|
| `VITE_API_BASE_URL` | URL pública da API (Railway domain) |

---

## 5. Observabilidade

### 5.1 Health check

`GET /health` retorna estado de cada componente:

```json
{
  "status": "healthy",
  "model": "loaded",
  "vectorstore": "loaded",
  "llm": "configured",
  "database": "connected"
}
```

Railway monitora este endpoint continuamente. Falha no health check aciona restart automático.

### 5.2 Logs estruturados

A API usa logging estruturado configurado em `app/core/logger.py`. Cada request logado com nível, timestamp, rota e tempo de resposta. Logs disponíveis no painel do Railway em tempo real.

### 5.3 O que seria monitorado em uma versão mais robusta

| Sinal | Método sugerido | Ação |
|---|---|---|
| Latência do `/predict` | Prometheus + Grafana | Alertar se p95 > 2s |
| Taxa de erro (5xx) | Railway built-in | Alertar se > 1% das requisições |
| Volume de predições | Tabela de logs no PostgreSQL | Análise de uso e sazonalidade |
| Distribuição de features de entrada | PSI calculado periodicamente | Detectar drift de dados |
| Distribuição de previsões | KS-test vs treino | Detectar shift de mercado |

---

## 6. Versionamento do Modelo

### Abordagem atual

O modelo em produção é determinado pelo artefato em `artifacts/model/`. O `metadata.json` registra:

```json
{
  "model_type": "XGBRegressor",
  "trained_at": "2026-04-08T11:44:36Z",
  "metrics": { ... },
  "feature_importance": { ... }
}
```

Não há model registry formal — a versão em produção é aquela incluída no build Docker mais recente.

### Evolução para versionamento formal

Para uma operação mais robusta, o fluxo ideal seria:

Treino local / CI → Avaliação automática (métricas vs threshold) → Registro no model registry (MLflow, W&B ou tabela no banco) → Artifact store (S3, GCS ou Railway Volume) → Deploy: API carrega versão mais recente aprovada no startup.

Isso permite rollback para versão anterior sem rebuild Docker, comparação histórica de métricas por versão e auditoria de quando cada modelo entrou em produção.

---

## 7. Evolução Futura da Arquitetura

A arquitetura atual é adequada para demonstração e escala inicial. Para um contexto de produção real com volume crescente, os caminhos naturais seriam:

**Separação entre serving e treinamento**  
O treino dentro do Docker é prático mas mistura responsabilidades. Em escala, o ideal é ter um pipeline de treinamento separado (Airflow, Prefect, ou GitHub Actions agendado) que produz artefatos e os empurra para um artifact store — o serviço de serving apenas carrega o artefato mais recente aprovado.

**Banco de inferência**  
Persistir todas as predições com features de entrada permite análise de uso, detecção de drift e, quando o preço real de venda for conhecido, cálculo do erro real do modelo em produção.

**Cache de predições**  
Combinações frequentes de features (imóveis populares) podem ser cacheadas com Redis para reduzir latência e custo computacional.

**Feature store**  
Se dados demográficos ou de mercado forem atualizados periodicamente, uma feature store centraliza o enriquecimento de dados na inferência sem necessidade de rebuild do modelo.
