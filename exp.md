# madeinweb-teste — Explicação da Estrutura

> Este arquivo explica em linguagem simples o que cada arquivo do projeto faz,
> como eles se conectam e onde você pode melhorar cada parte.

---

## Como o sistema funciona (visão geral)

Quando o usuário preenche um formulário na interface e clica em "Prever":

```
Usuário (Streamlit)
    │  envia dados do imóvel via HTTP
    ▼
FastAPI (porta 8001)
    │
    ├── /predict  → chama o XGBoost → retorna preço + intervalo P10/P90
    │
    ├── /chat     → busca documentos no FAISS (RAG)
    │               → monta prompt → chama GPT-4o-mini → retorna explicação
    │
    └── /health   → verifica se modelo, RAG e banco estão prontos
```

O **ML prevê**. O **RAG contextualiza**. O **LLM explica**. Nunca o inverso.

---

## Mapa das pastas

```
madeinweb-teste/
├── app/
│   ├── core/          ← infraestrutura (config, logs, utils)
│   ├── ml/            ← tudo sobre o modelo XGBoost
│   ├── rag/           ← knowledge base + busca vetorial
│   ├── api/           ← endpoints HTTP (FastAPI)
│   │   ├── routes/    ← define as URLs
│   │   ├── schemas/   ← valida inputs/outputs com Pydantic
│   │   └── services/  ← lógica de negócio (orquestração)
│   ├── db/            ← banco de dados (PostgreSQL, opcional)
│   └── ui/            ← interface Streamlit
├── data/
│   ├── raw/           ← kc_house_data.csv (dataset Kaggle)
│   └── knowledge_base/ ← documentos do RAG (.md e .csv)
├── artifacts/
│   ├── model/         ← modelo treinado (.joblib) + metadata.json
│   └── vectorstore/   ← índice FAISS gerado pelo RAG
└── tests/             ← testes automatizados (estrutura criada)
```

---

## app/core/ — A base de tudo

Esta pasta é a **infraestrutura compartilhada**. Qualquer outro módulo pode importar daqui.

---

### `app/core/config.py`

**O que faz:** Centraliza todas as configurações do sistema em um único objeto `settings`.

Em vez de ter `os.getenv("OPENAI_API_KEY")` espalhado em 10 arquivos diferentes,
qualquer módulo faz:
```python
from app.core.config import settings
print(settings.openai_api_key)
```

**Estrutura de classes:**
- `Settings` — classe base com todos os campos (portas, caminhos, keys)
- `DevSettings` — herda de Settings, define `log_level=DEBUG` por padrão
- `StagingSettings` — herda de Settings, avisa se OpenAI key não está configurada
- `ProdSettings` — herda de Settings, **falha no startup** se faltar `DATABASE_URL` ou `OPENAI_API_KEY`
- `get_settings()` — função com `@lru_cache` que lê `APP_ENV` e retorna a classe certa

**Validação cruzada:** Se você colocar `EMBEDDING_PROVIDER=openai` sem `OPENAI_API_KEY`,
a aplicação falha com mensagem clara antes de qualquer request.

**Onde melhorar:**
- Integrar com AWS Secrets Manager ou Railway Variables em produção
- Adicionar validação de formato dos caminhos de artefatos

---

### `app/core/logger.py`

**O que faz:** Cria loggers padronizados para cada módulo.

Uso em qualquer arquivo:
```python
from app.core.logger import get_logger
logger = get_logger(__name__)
logger.info("Modelo carregado")
```

**Diferença por ambiente:**
- **Desenvolvimento:** texto legível `2026-04-09 09:30 | INFO | app.ml.train | Mensagem`
- **Produção:** JSON estruturado `{"timestamp": "...", "level": "INFO", "message": "..."}` via `python-json-logger`

O JSON é necessário para que ferramentas como Datadog, CloudWatch ou Railway Logs
consigam indexar e filtrar os logs automaticamente.

**Onde melhorar:**
- Adicionar campos padrão ao JSON (ex: `request_id`, `user_id`) via `extra={}`
- Integrar com OpenTelemetry para traces distribuídos

---

### `app/core/utils.py`

**O que faz:** Funções pequenas e genéricas que não pertencem a nenhuma camada.

- `load_json(path)` / `save_json(data, path)` — leitura e escrita de JSON
- `ensure_dir(path)` — cria diretório se não existir
- `format_currency(value)` — formata número como `US$ 450,000`
- `@timer` — decorador que mede tempo de execução de qualquer função

**Onde melhorar:**
- Adicionar `async` versions das funções de I/O para uso em endpoints assíncronos

---

## app/ml/ — O núcleo de Machine Learning

Esta é a parte mais importante do projeto. O modelo XGBoost vive aqui.

---

### `app/ml/feature_engineering.py`

**O que faz:** Cria novas features a partir das colunas brutas do dataset.

Implementa a classe `HousePriceFeatureEngineer` que é um **transformer sklearn-compatível**.
Isso significa que pode entrar diretamente em um `Pipeline` e ser aplicado
de forma idêntica em treino e inferência — sem risco de inconsistência.

**Features criadas:**

| Feature | Cálculo | Por que importa |
|---|---|---|
| `house_age` | `2015 - yr_built` | Casas novas valem mais |
| `was_renovated` | `1 se yr_renovated > 0` | Flag de renovação |
| `years_since_renovation` | `2015 - yr_renovated` | Quanto tempo desde a última reforma |
| `living_lot_ratio` | `sqft_living / sqft_lot` | Densidade do imóvel no lote |
| `bath_bed_ratio` | `bathrooms / bedrooms` | Proporção de banheiros (conforto) |
| `has_basement` | `1 se sqft_basement > 0` | Flag de porão |
| `living15_ratio` | `sqft_living / sqft_living15` | Comparação com vizinhos |
| `sale_month` | Mês da venda | Sazonalidade do mercado |

**Onde melhorar:**
- Adicionar `price_per_sqft_neighborhood` (preço/sqft médio do zipcode)
- Adicionar `is_luxury` flag para grade >= 11
- Criar features de interação como `grade * sqft_living`

---

### `app/ml/preprocess.py`

**O que faz:** Carrega os dados e constrói o `ColumnTransformer` do sklearn.

**Funções de carregamento:**
- `load_house_data()` — lê o CSV, remove duplicatas, corrige outliers (bedrooms=33)
- `load_demographics()` — lê dados demográficos por zipcode (opcional)
- `merge_with_demographics()` — join dos dois datasets pelo zipcode

**Preprocessors:**
- `build_preprocessor()` — para o XGBoost:
  - Numéricas: `SimpleImputer(median)` (sem scaler, árvores não precisam)
  - Zipcode: `TargetEncoder` — substitui cada zipcode pela média suavizada do preço
- `build_baseline_preprocessor()` — para o Ridge:
  - Numéricas: `SimpleImputer + StandardScaler` (modelo linear precisa de escala)
  - Zipcode: `TargetEncoder` (mesma estratégia)

**Por que TargetEncoder e não OrdinalEncoder?**
O OrdinalEncoder atribuía números arbitrários (98001=0, 98002=1, ...).
O TargetEncoder substitui cada zipcode pelo preço médio naquele bairro,
capturando o sinal real de localização. Com `smoothing=10`, zipcodes raros
regridem para a média global, evitando overfitting.

**Onde melhorar:**
- Adicionar `CatBoostEncoder` como alternativa ao TargetEncoder (menos leakage)
- Implementar target encoding com cross-validation interna (`category_encoders.CrossValidationWrapper`)

---

### `app/ml/train.py`

**O que faz:** Orquestra o treinamento completo. É o "main" do módulo de ML.

**Fluxo ao rodar `python -m app.ml.train`:**

1. `prepare_data()` — carrega e faz split temporal
2. `train_baseline()` — treina Ridge como referência
3. `_find_optimal_n_estimators()` — early stopping em hold-out de validação
4. `train_xgboost()` — treina XGBoost p50 + p10 + p90
5. Calcula métricas, SHAP importance, medianas por zipcode
6. Salva todos os artefatos

**Split temporal (decisão importante):**
Em vez de split aleatório 80/20, treina em **2014** e testa em **2015**.
Isso reproduz o cenário real: o modelo foi treinado com dados históricos
e será usado para prever preços no futuro. Um split aleatório poderia
"vazar" informações do futuro para o treino.

**Early stopping:**
- Separa 10% do treino como validação interna
- Treina com `early_stopping_rounds=50`
- Para quando o erro de validação não melhora por 50 rodadas seguidas
- Encontra o `n_estimators` ótimo sem overfitting

**Modelos quantílicos (p10/p90):**
- Usa `objective='reg:quantileerror'` do XGBoost 2.0
- p10 = limite inferior do intervalo de confiança
- p90 = limite superior do intervalo de confiança
- ~80% das casas do teste devem ter o preço real dentro do intervalo

**Onde melhorar:**
- Adicionar `Optuna` para otimizar hiperparâmetros (max_depth, learning_rate, etc.)
- Usar `TimeSeriesSplit` do sklearn para validação cruzada temporal
- Adicionar `LightGBM` e `CatBoost` para um ensemble

---

### `app/ml/evaluate.py`

**O que faz:** Calcula métricas de avaliação do modelo.

**`RegressionMetrics` (dataclass):** Armazena 5 métricas:
- `RMSE` — erro quadrático médio (penaliza erros grandes)
- `MAE` — erro absoluto médio (mais interpretável em US$)
- `R²` — proporção da variância explicada (1.0 = perfeito)
- `MAPE` — erro percentual médio (independente de escala)
- `Median AE` — mediana dos erros absolutos (robusta a outliers)

**`compute_shap_importance()`:** Usa a biblioteca SHAP para calcular a importância
de cada feature na predição. É mais confiável que o `feature_importances_` nativo
do XGBoost porque considera interações entre features.

**`log_evaluation_report()`:** Imprime um relatório comparando treino vs. teste.
Se o gap de R² for maior que 0.05, avisa sobre possível overfitting.

**Onde melhorar:**
- Adicionar métricas por faixa de preço (erro em casas baratas vs. casas caras)
- Calcular coverage dos intervalos P10-P90 por zipcode
- Exportar relatório em HTML com plots

---

### `app/ml/model_registry.py`

**O que faz:** É o único lugar no código que sabe onde os artefatos estão em disco.

Qualquer módulo que precise carregar ou salvar o modelo usa este registry —
nunca acessa `artifacts/` diretamente. Isso facilita mudar o storage (S3, GCS)
sem alterar o resto do código.

**Funções:**
- `save_model()` / `load_model()` — pipeline XGBoost completo
- `save_preprocessor()` / `load_preprocessor()` — pipeline de pré-processamento
- `save_metadata()` / `load_metadata()` — JSON com métricas e configurações
- `save_quantile_models()` / `load_quantile_models()` — pipelines p10 e p90
- `artifacts_exist()` — verifica se o modelo foi treinado (usado no /health)
- `quantile_artifacts_exist()` — verifica se p10/p90 existem (opcional)

**Onde melhorar:**
- Integrar com MLflow para versionamento de modelos
- Adicionar suporte a carregamento de múltiplas versões simultâneas
- Implementar upload para S3/GCS para deploy em cloud

---

### `app/ml/predict.py`

**O que faz:** Interface pública de inferência. É aqui que a predição acontece.

**`PredictionResult` (dataclass):** Contrato entre o ML e a API. Carrega:
- `predicted_price` / `predicted_price_formatted` — o preço previsto
- `price_p10` / `price_p90` — intervalo de confiança
- `zipcode`, `sqft_living`, `bedrooms`, etc. — dados do imóvel (refletidos)
- `top_features` — top 5 features mais importantes (SHAP)
- `zipcode_median_price` / `price_vs_median_pct` — contexto de mercado

**`_load_artifacts()` com `@lru_cache`:** O modelo é carregado do disco apenas
na primeira chamada e mantido em memória. Requisições seguintes são 200ms+ mais rápidas.

**`predict_price(input_data)`:** Recebe um dict com os dados do imóvel, aplica
o pipeline completo (feature_eng → preprocessor → XGBoost) e retorna `PredictionResult`.

**`predict_batch(records)`:** Versão em lote — aplica os 3 modelos (p50, p10, p90)
em uma única passagem para eficiência.

**Onde melhorar:**
- Adicionar validação de distribuição (avisar se o input está fora do range do treino)
- Implementar cache de predições com Redis (hash do input como chave)

---

## app/api/ — A camada HTTP

Esta pasta expõe o ML como uma API REST usando FastAPI.

---

### `app/api/main.py`

**O que faz:** Ponto de entrada da API. Define o app FastAPI, CORS, handlers de erro
e o lifespan (startup/shutdown).

**Lifespan:** Roda no startup antes de aceitar requests:
- Verifica se o modelo existe (avisa se não)
- Verifica se o vectorstore existe (avisa se não)
- Inicializa o banco de dados (cria tabelas)
- Loga a URL dos docs

**Exception handlers globais:**
- `FileNotFoundError` → HTTP 503 (serviço indisponível) + dica de como resolver
- `ValueError` → HTTP 422 (dado inválido) + mensagem clara

**CORS:** Em desenvolvimento permite qualquer origem (`*`).
Em produção só permite a URL da própria UI.

**Onde melhorar:**
- Adicionar `slowapi` para rate limiting por IP
- Adicionar `GZipMiddleware` para comprimir responses grandes (batch predictions)

---

### `app/api/routes/predict.py`

**O que faz:** Define os 3 endpoints de predição.

| Endpoint | O que faz |
|---|---|
| `POST /predict` | Predição pura via XGBoost. Sem LLM. Rápida (<50ms). |
| `POST /predict/explain` | Predição + explicação automática via RAG+LLM. |
| `POST /predict/batch` | Predição em lote (até 100 imóveis por chamada). |

Cada endpoint chama o `prediction_service` (não o ML diretamente) e loga
a predição no banco de dados se disponível.

**Onde melhorar:**
- Adicionar `asyncio + ThreadPoolExecutor` no batch para paralelizar
- Versionar com prefixo `/v1/predict` para compatibilidade futura

---

### `app/api/routes/chat.py`

**O que faz:** Define os 2 endpoints de chat.

| Endpoint | O que faz |
|---|---|
| `POST /chat` | Responde perguntas usando RAG + LLM + histórico |
| `POST /chat/explain` | Gera explicação automática de uma predição (sem pergunta) |

**Stateless por design:** O histórico de conversa é enviado pelo cliente (Streamlit)
em cada request. A API não mantém estado — pode escalar horizontalmente sem Redis.

**Onde melhorar:**
- `StreamingResponse` com `openai.stream=True` para resposta token a token
- Rate limiting por sessão para evitar abuso

---

### `app/api/routes/health.py`

**O que faz:** Endpoint `GET /health` que verifica cada componente do sistema.

Retorna:
```json
{
  "status": "ok",
  "components": {
    "ml_model": "ready",
    "rag_vectorstore": "ready",
    "llm": "no_api_key",
    "database": "not_configured"
  }
}
```

Útil para Railway/Docker health checks e monitoramento.

**Onde melhorar:**
- Adicionar latência medida em cada componente
- Adicionar versão do modelo e data de treino na resposta

---

### `app/api/schemas/prediction.py`

**O que faz:** Define os contratos de entrada e saída do endpoint `/predict`.

**`HouseInput`:** Valida os dados do imóvel antes de qualquer processamento:
- Tipos corretos (int, float, str)
- Limites realistas (`bedrooms` de 0 a 20, `grade` de 1 a 13)
- Consistência entre campos (`sqft_above` não pode ser maior que `sqft_living`)

**`PredictionResponse`:** O que a API retorna, incluindo:
- Preço previsto + formatado
- Intervalo de confiança `price_p10` / `price_p90`
- Contexto de mercado (`zipcode_median_price`, `price_vs_median_pct`)
- Metadados do modelo (`model_version`, `top_features`)

**Onde melhorar:**
- Adicionar `model_id` para identificar qual versão do modelo foi usada
- Adicionar campo `extrapolation_warning` quando o input está fora do range do treino

---

### `app/api/schemas/chat.py`

**O que faz:** Define os contratos de entrada e saída do endpoint `/chat`.

**`PredictionContext`:** Versão compacta do `PredictionResponse` enviada pelo
cliente junto com cada mensagem — permite que a API seja stateless.

**`ChatRequest`:** Pergunta do usuário + contexto da predição + histórico de mensagens.

**`ChatResponse`:** Resposta do LLM + lista de fontes da KB usadas + flag `llm_available`.

---

### `app/api/services/prediction_service.py`

**O que faz:** Camada de orquestração entre o endpoint e o ML.

Responsabilidades:
1. Converte `HouseInput` (Pydantic) → dict para o modelo
2. Chama `predict_price()` do módulo ML
3. Busca a mediana do zipcode (banco → fallback metadata.json)
4. Calcula o desvio percentual vs. mediana
5. Monta o `PredictionResponse` com todos os campos

**Regra:** Nenhuma lógica de ML vive aqui. Este serviço apenas coordena.

**Onde melhorar:**
- Cache Redis com TTL de 1h para inputs idênticos
- Adicionar métricas de latência por etapa

---

### `app/api/services/explanation_service.py`

**O que faz:** Orquestra o fluxo RAG → Prompt → LLM para gerar explicações.

**`generate_initial_explanation(context)`:**
Chamado automaticamente após uma predição. Monta um prompt com:
- O resultado da predição (preço, zipcode, features importantes)
- Chunks da knowledge base relevantes para o zipcode/preço
- Instrução para gerar explicação em 3 parágrafos

**`answer_chat_question(request)`:**
Chamado quando o usuário faz uma pergunta. Monta um prompt com:
- Sistema + contexto da predição + chunks do RAG
- Histórico de até 6 turnos de conversa
- A pergunta atual

**Onde melhorar:**
- Adicionar detecção de intent (pergunta sobre limitações vs. sobre o imóvel vs. sobre o bairro)
- Personalizar o retrieval baseado no tipo de pergunta

---

### `app/api/services/rag_service.py`

**O que faz:** Ponte fina entre os services e o módulo de retrieval.

Traduz os schemas Pydantic (`PredictionContext`) para as chamadas do `retriever.py`
e formata os chunks recuperados em texto pronto para o prompt.

**Funções:**
- `get_prediction_context_chunks()` — chunks para explicar uma predição
- `get_chat_context_chunks()` — chunks para responder uma pergunta do chat
- `extract_sources()` — lista de arquivos usados (enviada ao cliente)
- `format_chunks_as_context()` — formata chunks como bloco de texto

---

### `app/api/services/llm_service.py`

**O que faz:** Responsabilidade única — chamar a API da OpenAI e tratar erros.

**`call_llm(messages)`:** Envia as mensagens formatadas e retorna `(resposta, llm_disponivel)`.

**Fallback gracioso:** Se o LLM falhar (sem key, sem créditos, timeout), retorna uma
mensagem de fallback em vez de um erro HTTP 500. A predição de preço continua válida.
O `llm_available=False` no response avisa o cliente.

**Detecção de tipo de erro:** Mensagens diferentes para quota esgotada, key inválida
ou timeout — mais útil do que uma mensagem genérica.

**Onde melhorar:**
- Adicionar retry com backoff exponencial para erros de rate limit
- Suporte a streaming (`stream=True`) para resposta token a token

---

## app/rag/ — Knowledge Base e Retrieval

---

### `app/rag/build_kb.py`

**O que faz:** Lê os documentos da `data/knowledge_base/`, transforma em vetores
e salva o índice FAISS.

**Executar uma vez:** `python -m app.rag.build_kb` (ou `make build-kb`)

**Documentos processados:**
- `business_context.md` — contexto do mercado imobiliário de King County
- `feature_dictionary.md` — o que cada feature significa e como afeta o preço
- `model_limitations.md` — honesto sobre o que o modelo não sabe
- `eda_summary.md` — estatísticas-chave do dataset
- `zipcode_insights.csv` — cada linha = 1 documento = 1 zipcode

**Estratégia de chunking:**
- Markdown: `RecursiveCharacterTextSplitter` com chunks de 600 chars e 80 de overlap
- CSV: cada linha é um documento independente (evita misturar zipcodes num chunk)

**Onde melhorar:**
- Reindexação incremental (só reindexar arquivos modificados)
- `FlashRank` para reranking dos chunks antes de enviar ao LLM

---

### `app/rag/embeddings.py`

**O que faz:** Configura o modelo de embeddings (converte texto em vetores).

**Dois provedores controlados por `EMBEDDING_PROVIDER` no `.env`:**
- `local` (padrão): `fastembed` com modelo `BAAI/bge-small-en-v1.5` — gratuito, ONNX, 33MB
- `openai`: `text-embedding-3-small` da OpenAI — melhor qualidade, exige créditos

**Por que fastembed no padrão?** Sem PyTorch, sem problema de path longo no Windows,
funciona offline, zero custo.

**Onde melhorar:**
- Fine-tunar o `bge-small` com vocabulário imobiliário de King County
- Adicionar suporte ao `Cohere Embed` como terceira opção

---

### `app/rag/retriever.py`

**O que faz:** Dado um contexto, recupera os trechos mais relevantes da KB.

**`RetrievedChunk` (dataclass):** Trecho recuperado com:
- `content` — o texto do chunk
- `source` — qual arquivo (ex: `feature_dictionary.md`)
- `chunk_type` — `"markdown"` ou `"zipcode"`
- `relevance_score` — distância L2 (menor = mais relevante)
- `zipcode` — preenchido só para chunks de zipcode

**`retrieve_for_prediction()`:** Constrói automaticamente a query de busca:
`"zipcode 98103 | preço médio-alto entre 500k e 800k | grade 9 qualidade | área 2100 sqft"`

Garante que ao menos 1 chunk do zipcode específico esteja nos resultados.

**`retrieve_for_chat()`:** Augmenta a pergunta do usuário com o contexto da predição
antes de fazer a busca semântica.

**Onde melhorar:**
- Metadata filtering por `chunk_type` antes da busca semântica
- Chunks hierárquicos com `LlamaIndex`

---

### `app/rag/prompt_builder.py`

**O que faz:** Monta os prompts que serão enviados ao LLM.

**`SYSTEM_PROMPT`:** Define a personalidade e regras do assistente:
- Você é um explicador, não um previsor
- Não questione nem substitua o preço do ML
- Responda sempre em português
- Seja honesto sobre limitações

**`build_explanation_prompt()`:** Para a explicação automática.
**`build_chat_prompt()`:** Para o chat com histórico.
**`build_simple_chat_prompt()`:** Versão simplificada quando só há strings.

**Onde melhorar:**
- Adicionar few-shot examples no system prompt (exemplos de boas explicações)
- Personalizar o tom baseado na faixa de preço (luxo vs. acessível)

---

## app/db/ — Banco de Dados (opcional)

O banco é **completamente opcional** — o sistema funciona sem ele.
Se `DATABASE_URL` não estiver no `.env`, tudo funciona em modo degradado.

---

### `app/db/models.py`

**O que faz:** Define as 3 tabelas do banco usando SQLAlchemy ORM.

**`PredictionLog`:** Registra cada predição feita:
- Todos os inputs do imóvel
- O preço previsto
- A mediana do zipcode e o desvio percentual
- Relacionamento com chat_messages

**`ZipcodeStats`:** Estatísticas de mercado por zipcode:
- Populada no startup a partir do `metadata.json` e do `zipcode_insights.csv`
- É a fonte principal para enriquecer respostas com contexto de mercado

**`ChatMessage`:** Uma mensagem de chat:
- `session_id` para agrupar mensagens de uma mesma sessão
- `role` ("user" ou "assistant")
- `content` + `sources` + FK para a predição que originou a conversa

**Onde melhorar:**
- Adicionar índice em `PredictionLog.zipcode` + `created_at` para queries de análise
- Adicionar `PredictionLog.model_version` para monitorar drift por versão

---

### `app/db/session.py`

**O que faz:** Gerencia a conexão com o banco de dados.

Cria o `engine` SQLAlchemy a partir de `DATABASE_URL`. Se a URL não existir
ou a conexão falhar, `db_available()` retorna `False` e o sistema continua sem banco.

---

### `app/db/init_db.py`

**O que faz:** Inicializa o banco no startup da API.

- Cria as tabelas se não existirem (`Base.metadata.create_all`)
- Faz seed dos zipcodes na tabela `zipcode_stats` a partir do `metadata.json`
  e do `zipcode_insights.csv`

---

### `app/db/crud.py`

**O que faz:** Funções de acesso ao banco (Create, Read).

- `log_prediction()` — salva uma predição no audit log
- `get_zipcode_median()` — busca a mediana de preço de um zipcode
- `get_prediction_stats()` — retorna estatísticas para o `/health`

---

## app/ui/ — Interface Streamlit

---

### `app/ui/streamlit_app.py`

**O que faz:** Interface visual do usuário.

**Regra:** Nenhuma lógica de ML vive aqui. Tudo é feito via chamadas HTTP à API.

**O que a UI faz:**
1. Sidebar com formulário (selectbox de zipcode → preenche lat/long automaticamente)
2. Clique em "Prever" → POST /predict → exibe card de preço com gradiente
3. Exibe intervalo de confiança P10-P90 se disponível
4. Chama POST /predict/explain → exibe explicação automática
5. Chat com histórico persistido em `st.session_state`
6. Gráfico de feature importance (SHAP)

**Onde melhorar:**
- `st.map()` ou `pydeck` com pin no zipcode selecionado
- `st.write_stream()` para streaming da resposta do LLM token a token
- Comparador de múltiplos imóveis lado a lado

---

## Arquivos raiz

| Arquivo | O que faz |
|---|---|
| `.env` | Variáveis de ambiente locais (não versionar) |
| `.env.example` | Template com todas as variáveis necessárias |
| `requirements.txt` | Todas as dependências Python com versões fixas |
| `Makefile` | Atalhos: `make train`, `make build-kb`, `make api`, `make ui` |
| `Dockerfile` | Imagem Docker da API |
| `docker-compose.yml` | Orquestração API + banco local |

---

## Como os módulos se conectam

```
train.py
    │ usa
    ├── feature_engineering.py  (HousePriceFeatureEngineer)
    ├── preprocess.py           (build_preprocessor, load_house_data)
    ├── evaluate.py             (compute_metrics, compute_shap_importance)
    └── model_registry.py       (save_all)

predict.py
    │ usa
    └── model_registry.py       (load_model, load_quantile_models)

prediction_service.py
    │ usa
    ├── predict.py              (predict_price, PredictionResult)
    └── db/crud.py              (get_zipcode_median)

explanation_service.py
    │ usa
    ├── rag_service.py          (get_prediction_context_chunks)
    └── llm_service.py          (call_llm)

rag_service.py
    │ usa
    └── retriever.py            (retrieve_for_prediction, retrieve_for_chat)

retriever.py
    │ usa
    └── embeddings.py           (get_embeddings)

routes/predict.py
    │ usa
    └── prediction_service.py   (predict_single, predict_many)

routes/chat.py
    │ usa
    └── explanation_service.py  (answer_chat_question, generate_initial_explanation)
```

---

## Onde melhorar por nível de dificuldade

### Fácil (1-2h)
- `evaluate.py`: adicionar métricas por faixa de preço
- `llm_service.py`: retry com backoff exponencial
- `health.py`: adicionar latência medida de cada componente

### Médio (meio dia)
- `train.py`: adicionar `Optuna` para otimização de hiperparâmetros
- `retriever.py`: adicionar metadata filtering por `chunk_type`
- `streamlit_app.py`: adicionar mapa interativo com `pydeck`

### Avançado (1-2 dias)
- `preprocess.py`: target encoding com cross-validation interna
- `model_registry.py`: integração com MLflow para versionamento
- `llm_service.py`: streaming com `StreamingResponse` + `st.write_stream()`
- `build_kb.py`: reindexação incremental (só reindexar arquivos modificados)
