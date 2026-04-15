# madeinweb — Previsão de Preços de Imóveis

> Case técnico de Data Science: modelo preditivo tabular + camada de explicação via RAG e LLM para estimativa de preço de imóveis em King County, WA.

**[Acessar aplicação em produção →](https://dazzling-endurance-production.up.railway.app/)**

---

## Visão Geral

O projeto responde uma pergunta objetiva: **quanto vale este imóvel?**

Para isso, combina um modelo XGBoost treinado sobre 21.000+ transações reais com uma interface interativa que apresenta a estimativa de preço, o intervalo de confiança (P10–P90) e uma camada conversacional capaz de explicar os fatores que determinaram aquele resultado.

A estrutura foi pensada para cobrir os quatro pilares do desafio técnico:

| Pilar | Como está coberto |
|---|---|
| Análise e entendimento dos dados | EDA documentada, features derivadas com racional explícito |
| Modelagem de ML | XGBoost com split temporal, early stopping e quantile regression |
| Estratégia de deploy | FastAPI + React + Docker + Railway, dois serviços independentes |
| Aprendizado contínuo | Estratégia documentada de reentreino, monitoramento e promoção de modelos |
| Comunicação com stakeholders | Interface em português, chat explicativo, documentação em `docs/` |

---

## Demonstração

**Aplicação:** https://dazzling-endurance-production.up.railway.app/

### Estado inicial — formulário de entrada

![Estado inicial da interface](docs/screenshots/01_form_empty.png)

Painel esquerdo com controles para quartos, banheiros, área interna, andares, qualidade construtiva (grade 1–13), condição, frente para a água e vista. Painel direito com o assistente de IA e perguntas sugeridas.

### Resultado da previsão

![Resultado da previsão com intervalo de confiança](docs/screenshots/02_prediction_result.png)

Estimativa central com intervalo P10–P90, comparação com a mediana do zipcode, resumo das características do imóvel e localização.

### Chat explicativo

![Chat explicando os fatores do preço](docs/screenshots/03_chat_explanation.png)

O assistente explica em linguagem natural por que o modelo chegou naquele preço, quais fatores pesaram mais e o que poderia ser feito para aumentar o valor do imóvel.

---

## Arquitetura da Solução

```
┌─────────────────────────────────────────────────────────────┐
│                     React (Frontend)                        │
│   Formulário → Resultado → Chat (3 painéis responsivos)     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / JSON
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (Backend)                        │
│   POST /predict   POST /chat   GET /health                  │
│                                                             │
│   ┌──────────────────┐    ┌──────────────────────────────┐  │
│   │   ML Pipeline    │    │       RAG + LLM              │  │
│   │                  │    │                              │  │
│   │  XGBoost (p50)   │    │  FAISS vectorstore           │  │
│   │  Quantis p10/p90 │    │  Knowledge base (5 docs)     │  │
│   │  Preprocessador  │    │  OpenAI / Groq               │  │
│   └──────────────────┘    └──────────────────────────────┘  │
│                                                             │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  PostgreSQL — log de predições (opcional)            │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Hierarquia de responsabilidades:**

| Camada | Papel |
|---|---|
| **ML (XGBoost)** | Responsável pela previsão de preço. É o núcleo da solução. |
| **Quantile Regression** | Gera o intervalo P10–P90 — mede a faixa provável, não apenas o ponto central. |
| **RAG (FAISS)** | Recupera contexto relevante da knowledge base para enriquecer as respostas do chat. |
| **LLM (OpenAI / Groq)** | Explica a previsão em linguagem natural. Não realiza previsão de preço. |
| **PostgreSQL** | Persiste logs de predição para análise futura e monitoramento. |

> O LLM **não estima preços**. O preço vem exclusivamente do modelo XGBoost treinado. O chat explica o que o modelo calculou.

Diagramas detalhados: [`diagrams/`](diagrams/)  
Documentação completa do deploy: [`docs/3-estrategia-de-deploy.md`](docs/3-estrategia-de-deploy.md)

---

## Entendimento dos Dados

### Datasets utilizados

| Dataset | Registros | Fonte | Papel |
|---|---|---|---|
| `kc_house_data.csv` | 21.613 vendas | King County Assessor | Dataset principal de treino e teste |
| `zipcode_demographics.csv` | 70 zipcodes | Dados demográficos públicos | Enriquecimento por localização |
| `future_unseen_examples.csv` | Amostras sintéticas | Gerado para o projeto | Validação de inferência em dados novos |

### Como os dados foram combinados

O dataset de vendas e os dados demográficos foram integrados via `zipcode` como chave de junção. Isso permite que o modelo capture não apenas as características físicas do imóvel, mas também o perfil socioeconômico do bairro.

### Distribuição do preço (target)

| Estatística | Valor |
|---|---|
| Mediana | US$ 450.000 |
| Média | US$ 540.088 |
| Desvio padrão | US$ 367.127 |
| P25 | US$ 321.950 |
| P75 | US$ 645.000 |
| Máximo | US$ 7.700.000 |

A distribuição é fortemente assimétrica à direita (skewness ≈ 4.0). O modelo aplica `log1p` no target durante o treino e `expm1` na inferência para trabalhar em escala logarítmica e reduzir o impacto de outliers.

### Principais desafios de qualidade

- **Assimetria do target:** resolvida com transformação logarítmica
- **Dados históricos:** o dataset cobre 2014–2015; os valores absolutos refletem o nível de preços daquele período
- **Outliers extremos:** imóvel com 33 quartos (erro de digitação), imóveis abaixo de US$ 75k — removidos no pré-processamento
- **Waterfront escasso:** apenas 0,75% dos imóveis têm frente para a água, o que gera desequilíbrio nas estimativas desse segmento

Documentação completa: [`docs/1-analise-e-entendimento-dos-dados.md`](docs/1-analise-e-entendimento-dos-dados.md)

---

## Pipeline de Machine Learning

### Features

O modelo usa **24 features**: 16 do dataset original + 8 derivadas via feature engineering.

**Features derivadas com maior impacto:**

| Feature | Racional |
|---|---|
| `house_age` | Diferença entre 2015 e `yr_built` — captura depreciação e valor histórico |
| `was_renovated` | Flag binária — imóveis reformados têm mediana 22% superior |
| `years_since_renovation` | Frescor da renovação — reformas recentes valem mais |
| `living_lot_ratio` | `sqft_living / sqft_lot` — densidade de ocupação; proxy de perfil urbano vs rural |
| `bath_bed_ratio` | Ratio banheiros/quartos — imóveis de alto padrão tendem a ter ratio alto |
| `living15_ratio` | Imóvel em relação aos vizinhos — ser maior que a vizinhança tem prêmio |

### Modelos avaliados

| Modelo | Abordagem | Descarte |
|---|---|---|
| Ridge (baseline) | Regressão linear com regularização L2 + log1p | Mantido como baseline de comparação |
| XGBoost | Gradient boosting com árvores de decisão | **Modelo final** |

### Modelo final: XGBoost

**Configuração:**
- Split: **temporal** — treino em vendas anteriores a jan/2015, teste em vendas posteriores (simula previsão do futuro)
- Early stopping com 10% de holdout interno para definir `n_estimators` ideal
- Três modelos treinados: ponto central (p50), limite inferior (p10) e superior (p90) com quantile regression
- Target transformado com `log1p`; previsão reconvertida com `expm1`

### Resultados

| Métrica | Baseline (Ridge) | XGBoost Final | Melhoria |
|---|---|---|---|
| **RMSE** | US$ 184.856 | US$ 125.845 | −32% |
| **MAE** | US$ 108.237 | US$ 62.083 | −43% |
| **R²** | 0.764 | **0.891** | +17pp |
| **MAPE** | 19.66% | **11.24%** | −8pp |
| **Median AE** | US$ 67.751 | US$ 34.330 | −49% |

*Métricas avaliadas no conjunto de teste (4.287 registros, jan–mai 2015). Gap R² treino-teste: 0.083 — sem sinais de overfitting expressivo.*

**Cobertura do intervalo P10–P90:** o intervalo captura o preço real em ~80% dos casos no conjunto de teste, com largura média de ~US$ 194.000.

### Importância das variáveis

As duas métricas de importância (gain do XGBoost e SHAP) apontam para o mesmo conjunto de variáveis determinantes, com divergência reveladora em `grade` vs `lat`:

| Feature | Gain (rank) | SHAP (rank) | Interpretação |
|---|---|---|---|
| `lat` | 3º | **1º** | Localização tem impacto marginal maior que o gain sugere |
| `sqft_living` | 2º | 2º | Área útil é consistentemente o segundo fator mais relevante |
| `grade` | **1º** | 3º | Grade domina o gain mas tem impacto marginal menor que a lat |
| `waterfront` | 4º | 10º+ | Flag binária com gain alto mas impacto SHAP distribuído |
| `long` | 9º | 4º | Longitude captura variação leste-oeste dentro do condado |

Resultado completo: [`results/feature_importance.csv`](results/feature_importance.csv)  
Documentação de decisões: [`docs/2-desenvolvimento-do-modelo.md`](docs/2-desenvolvimento-do-modelo.md)

---

## Camada de Explicação (RAG + LLM)

A interface inclui um assistente conversacional que responde perguntas sobre o imóvel avaliado, o mercado e o funcionamento do modelo. Esta camada é **complementar** ao modelo de ML, não substituta.

**O que o chat faz:**
- Explica em linguagem natural por que o preço foi estimado naquele valor
- Responde perguntas sobre o mercado de King County (sazonalidade, segmentos, fatores de valorização)
- Descreve o impacto de cada feature na previsão
- Sugere o que poderia aumentar ou diminuir o valor estimado

**O que o chat não faz:**
- Não estima preços — isso é responsabilidade exclusiva do XGBoost
- Não tem acesso a dados externos ou preços em tempo real
- Não substitui avaliação imobiliária profissional

**Arquitetura RAG:**

```
Pergunta do usuário
      ↓
Embedding (fastembed local ou OpenAI)
      ↓
Busca vetorial no FAISS (top-4 trechos)
      ↓
Prompt montado com: contexto recuperado + dados do imóvel + previsão ML
      ↓
LLM (GPT-4o-mini via OpenAI ou Llama 3.1 via Groq)
      ↓
Resposta em linguagem natural
```

**Knowledge base** (5 documentos):
- `eda_summary.md` — achados estatísticos da análise exploratória
- `feature_dictionary.md` — dicionário completo de variáveis
- `business_context.md` — contexto do mercado imobiliário de King County
- `model_limitations.md` — limitações técnicas e de escopo do modelo
- `zipcode_insights.csv` — medianas por zipcode

---

## Estratégia de Deploy

### Stack em produção

| Componente | Tecnologia | Hospedagem |
|---|---|---|
| Frontend | React + TypeScript + Tailwind | Railway (serviço 2) |
| Backend / API | FastAPI + Uvicorn | Railway (serviço 1) |
| Banco de dados | PostgreSQL | Railway (managed) |
| Containerização | Docker | Dockerfile por serviço |

### Dois serviços independentes no Railway

**API (raiz do repositório):**  
O `Dockerfile` principal usa multi-stage build: baixa o dataset KC House, treina o XGBoost, constrói o índice FAISS e empacota tudo na imagem final. O modelo é treinado no build — não depende de volume externo.

**Frontend (`frontend/`):**  
Build separado com `VITE_API_BASE_URL` passado como build arg. A variável deve ser marcada como *Available at Build Time* no painel do Railway.

**Variáveis de ambiente necessárias:**

```
# API
APP_ENV=production
LLM_PROVIDER=openai          # ou groq
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
CORS_ORIGINS=https://seu-frontend.up.railway.app

# Frontend (build arg)
VITE_API_BASE_URL=https://sua-api.up.railway.app
```

Documentação completa: [`docs/3-estrategia-de-deploy.md`](docs/3-estrategia-de-deploy.md)

---

## Aprendizado Contínuo

O modelo atual foi treinado com dados de 2014–2015. Uma estratégia de reentreino permitiria manter a relevância à medida que o mercado evolui.

**Gatilhos para reentreino:**
- Degradação de MAPE > 5pp em relação ao baseline histórico
- Acúmulo de N novos registros com preço realizado confirmado
- Drift detectado na distribuição de features de entrada (KS-test ou PSI)

**Pipeline de promoção segura:**
1. Reentreinar com dados novos + histórico
2. Avaliar no conjunto de holdout temporal
3. Comparar métricas com o modelo em produção
4. Promover apenas se R² ≥ modelo atual e MAPE ≤ modelo atual
5. Deploy com rollback automático se health check falhar

Documentação completa: [`docs/4-aprendizado-continuo.md`](docs/4-aprendizado-continuo.md)

---

## Estrutura do Repositório

```
madeinweb/
├── app/
│   ├── api/            # FastAPI — rotas, schemas, serviços
│   ├── ml/             # Pipeline de ML: treino, inferência, avaliação
│   ├── rag/            # Knowledge base, embeddings, retriever
│   ├── ui/             # Interface Streamlit (alternativa à React)
│   ├── core/           # Configuração, logging, utilitários
│   └── db/             # Persistência de logs de predição (SQLAlchemy)
├── frontend/           # React + TypeScript + Tailwind (interface principal)
├── data/
│   ├── raw/            # Datasets originais (KC House, demographics, exemplos futuros)
│   ├── processed/      # Dados transformados
│   └── knowledge_base/ # Documentos para o RAG
├── artifacts/
│   ├── model/          # Modelo treinado, preprocessador, metadata.json
│   └── vectorstore/    # Índice FAISS
├── diagrams/           # Diagramas de arquitetura (Mermaid + PNG)
├── docs/               # Documentação técnica e executiva
├── results/            # Métricas, importância de features, predições em dados novos
├── notebooks/          # Análise exploratória e modelagem (em desenvolvimento)
├── scripts/            # Scripts auxiliares (download de dados)
├── tests/              # Testes automatizados
├── Dockerfile          # Build da API (multi-stage: treino + RAG)
├── docker-compose.yml  # Orquestração local
├── Makefile            # Interface de comandos do projeto
└── requirements.txt    # Dependências Python
```

---

## Como Executar Localmente

### Pré-requisitos

- Python 3.11+
- Node.js 18+ (para o frontend React)
- Docker (opcional, para execução containerizada)
- Chave de API: OpenAI (`sk-...`) ou Groq (`gsk-...`)

### 1. Configurar ambiente Python

```bash
git clone https://github.com/seu-usuario/madeinweb.git
cd madeinweb

python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# ou: .venv\Scripts\activate  # Windows

pip install -r requirements.txt
cp .env.example .env
# Edite .env: defina LLM_PROVIDER e a chave correspondente
```

### 2. Treinar o modelo

```bash
make train
# Saída: artifacts/model/house_price_model.joblib + metadata.json
```

### 3. Construir a knowledge base

```bash
make build-kb
# Saída: artifacts/vectorstore/index.faiss
```

### 4. Iniciar a API

```bash
make api
# API disponível em http://localhost:8001
# Documentação: http://localhost:8001/docs
```

### 5. Iniciar o frontend React

```bash
cd frontend
cp .env.example .env.local
# Defina VITE_API_BASE_URL=http://localhost:8001
npm install
npm run dev
# Interface em http://localhost:5173
```

### 6. Execução com Docker (API + banco)

```bash
docker-compose up --build
```

> O build Docker inclui o treinamento do modelo e a construção do índice FAISS. Pode levar 10–20 minutos na primeira execução, dependendo dos recursos disponíveis.

### Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Status do serviço e disponibilidade dos artefatos |
| `POST` | `/predict` | Estimativa de preço + intervalo P10–P90 |
| `POST` | `/chat` | Pergunta contextualizada ao assistente |
| `GET` | `/docs` | Documentação interativa Swagger |

---

## Stack Técnica

| Categoria | Tecnologias |
|---|---|
| **ML** | pandas, numpy, scikit-learn, XGBoost, SHAP |
| **API** | FastAPI, Pydantic v2, Uvicorn, SQLAlchemy |
| **RAG** | LangChain, FAISS, fastembed (local) / OpenAI Embeddings |
| **LLM** | OpenAI (GPT-4o-mini), Groq (Llama 3.1 8B) |
| **Frontend** | React 18, TypeScript, Tailwind CSS, shadcn/ui, Vite |
| **Banco** | PostgreSQL |
| **Infra** | Docker, Railway |

---


## Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/resumo-executivo.md`](docs/resumo-executivo.md) | Resumo executivo para liderança e negócio |
| [`docs/1-analise-e-entendimento-dos-dados.md`](docs/1-analise-e-entendimento-dos-dados.md) | Análise detalhada dos dados e EDA |
| [`docs/2-desenvolvimento-do-modelo.md`](docs/2-desenvolvimento-do-modelo.md) | Decisões técnicas de modelagem com racional |
| [`docs/3-estrategia-de-deploy.md`](docs/3-estrategia-de-deploy.md) | Arquitetura de produção e infraestrutura |
| [`docs/4-aprendizado-continuo.md`](docs/4-aprendizado-continuo.md) | Estratégia de reentreino e monitoramento |
| [`docs/5-comunicacao-com-stakeholders.md`](docs/5-comunicacao-com-stakeholders.md) | Como apresentar os resultados para diferentes públicos |

---

*Desenvolvido como case técnico — Data Science + MLOps + GenAI.*
