# madeinweb-teste

> Solução end-to-end para previsão de preços de imóveis com Machine Learning + GenAI.

---

## Visão geral

O **madeinweb-teste** é um produto de dados que combina um modelo preditivo tabular com uma camada de inteligência generativa para oferecer não apenas uma estimativa de preço, mas uma **explicação contextualizada em linguagem natural**.

O projeto foi construído como um case técnico para demonstrar capacidade em:
- Engenharia de features e modelagem preditiva com dados tabulares
- Arquitetura orientada a serviços com FastAPI
- Implementação de RAG (Retrieval-Augmented Generation) pragmático
- Interface interativa com Streamlit
- Deploy containerizado via Docker e Railway

---

## Arquitetura

```
Usuário → UI (Streamlit)
             ↓
          API (FastAPI)
         /           \
   ML Pipeline     RAG + LLM
  (XGBoost)     (FAISS + GPT)
       ↓               ↓
   Previsão     Contexto & Explicação
         \           /
          Resposta Final
```

### Hierarquia de responsabilidades

| Camada | Responsabilidade |
|---|---|
| **ML** | Prever o preço com precisão e robustez |
| **RAG** | Recuperar contexto relevante da knowledge base |
| **LLM** | Explicar a previsão em linguagem natural |
| **Chat** | Responder perguntas usando os três anteriores |

> O modelo de ML é o protagonista. O RAG não prevê preço. O LLM não substitui o modelo.

---

## Stack

| Categoria | Tecnologia |
|---|---|
| ML | pandas, numpy, scikit-learn, XGBoost, SHAP |
| API | FastAPI, Pydantic, Uvicorn |
| RAG | LangChain, FAISS, OpenAI Embeddings |
| UI | Streamlit |
| Deploy | Docker, Railway |

---

## Estrutura do projeto

```
madeinweb-teste/
├── app/
│   ├── api/            # FastAPI — rotas, schemas, serviços
│   ├── ml/             # Pipeline de ML: treino, inferência, avaliação
│   ├── rag/            # Knowledge base, embeddings, retriever
│   ├── ui/             # Interface Streamlit
│   ├── core/           # Configuração, logging, utilitários
│   └── db/             # Persistência opcional (SQLAlchemy)
├── data/
│   ├── raw/            # Dados originais (King County Housing)
│   ├── processed/      # Dados transformados
│   └── knowledge_base/ # Documentos para o RAG
├── artifacts/
│   ├── model/          # Modelo treinado, preprocessador, metadados
│   └── vectorstore/    # Índice FAISS
├── notebooks/          # Exploração e análise
├── tests/              # Testes automatizados
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## Como executar localmente

### 1. Pré-requisitos

- Python 3.11+
- Docker (opcional)
- Chave de API da OpenAI ou Groq

### 2. Configurar ambiente

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/madeinweb-teste.git
cd madeinweb-teste

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com LLM_PROVIDER e sua chave (OPENAI_API_KEY ou GROQ_API_KEY)
```

### 3. Treinar o modelo

```bash
make train
```

### 4. Construir a knowledge base

```bash
make build-kb
```

### 5. Iniciar a API

```bash
make api
```

### 6. Iniciar a UI

```bash
make ui
```

### 7. Tudo de uma vez (Docker)

O `Dockerfile` é **multi-stage**: na fase de build baixa o CSV público do KC House, roda `python -m app.ml.train` e `python -m app.rag.build_kb`; a imagem final só leva código + `artifacts/` + `data/knowledge_base/`. O build pode levar **10–20 minutos** e precisa de **RAM suficiente** (treino XGBoost + FAISS).

```bash
docker-compose up --build
# ou só a API (mesma imagem):
docker build -t house-price-copilot-api .
```

Variável opcional no build (Railway **Docker Build Args** ou `docker build --build-arg`):

- `KC_HOUSE_DATA_URL` — força uma URL; se vazio, o script tenta mirrors (GitHub raw). O bucket `storage.googleapis.com/mledu-datasets` costuma devolver **403** em CI/build.

### 8. Railway (API + React)

**API (raiz do repo):** `Dockerfile` na raiz — treino + RAG no build. Variáveis: `DATABASE_URL` (referência ao Postgres), `APP_ENV`, chaves LLM, etc.

**React (`frontend/`):** segundo serviço na Railway com **Root Directory** = `frontend` e o `frontend/Dockerfile`. Variável de build **`VITE_API_BASE_URL`** = URL pública da API (marcar *Available at Build Time*). Passos detalhados em `frontend/README.md`.

Depois do front ter domínio próprio, em `APP_ENV=production` na API define **`CORS_ORIGINS`** com esse URL.

---

## Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Status do serviço |
| POST | `/predict` | Previsão de preço |
| POST | `/chat` | Pergunta ao copiloto |

---

## Dataset

O projeto usa o **King County House Sales Dataset** (Kaggle), com dados de vendas de imóveis em King County, Seattle (WA), enriquecidos com dados demográficos por zipcode.

---

## Próximos passos

- [ ] Adicionar monitoramento de drift de dados
- [ ] Implementar cache de predições com Redis
- [ ] Adicionar suporte a múltiplos modelos (model registry)
- [ ] Expandir a knowledge base com dados de mercado imobiliário
- [ ] Dashboard de performance do modelo

---

## Autor

Desenvolvido como case técnico para demonstração de skills em ML + GenAI.
