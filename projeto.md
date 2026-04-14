# madeinweb-teste — Documentação Técnica do Projeto

> Retrospectiva completa: o que foi feito, como foi feito, por que foi feito assim e o que pode ser melhorado.

---

## Visão geral

O **madeinweb-teste** é uma solução end-to-end de previsão de preços de imóveis em King County (Seattle, WA) que combina três camadas:

1. **Machine Learning** — XGBoost treinado em 21k+ vendas reais (2014–2015)
2. **RAG** — Knowledge base vetorial com contexto de mercado, features e limitações
3. **LLM** — GPT-4o-mini para explicações em linguagem natural e chat contextual

A arquitetura foi desenhada para um **case técnico de Cientista de Dados GenAI**, com foco em apresentar ML como protagonista e GenAI como camada complementar de explicação — não como substituto do modelo.

---

## Arquitetura geral

```
Usuário
  │
  ▼
Streamlit UI (porta 8501)
  │  consome via HTTP
  ▼
FastAPI (porta 8001)
  ├── /predict   →  ML Pipeline (XGBoost)
  ├── /chat      →  RAG (FAISS) + LLM (OpenAI)
  └── /health    →  Status dos componentes
        │
        ├── app/ml/          ← núcleo preditivo
        ├── app/rag/         ← retrieval e contexto
        └── app/api/services ← orquestração
```

### Hierarquia respeitada

```
ML prevê  →  RAG contextualiza  →  LLM explica  →  UI apresenta
```

Nunca o inverso. O LLM não toca nos dados do modelo. O RAG não prevê preço.

---

## Fase 1 — Fundação do projeto

### O que foi feito
- Estrutura de pastas modular com separação clara de responsabilidades
- `app/core/config.py` com `pydantic-settings` para gerenciamento de variáveis de ambiente
- `app/core/logger.py` com logger centralizado configurável por ambiente
- `app/core/utils.py` com funções utilitárias reutilizáveis
- `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `Makefile`
- `Dockerfile` e `docker-compose.yml` como esqueletos para deploy

### Por que foi feito assim
- **pydantic-settings**: valida tipos em tempo de importação e expõe um objeto `settings` único — elimina `os.getenv()` espalhado pelo código
- **lru_cache no get_settings()**: singleton sem variável global explícita
- **Logger com `get_logger(__name__)`**: rastreabilidade de qual módulo emitiu cada log
- **`__init__.py` em todos os pacotes**: projeto importável desde o início, evita erros em testes

### O que pode melhorar

| Melhoria | Como implementar |
|---|---|
| Múltiplos ambientes de configuração | Criar `Settings` base e subclasses `DevSettings`, `ProdSettings`, selecionadas pelo `APP_ENV` |
| Validação de configuração no startup | Adicionar método `validate()` em `Settings` que verifica dependências cruzadas (ex: se `EMBEDDING_PROVIDER=openai`, exige `OPENAI_API_KEY`) |
| Structured logging em produção | Substituir o formatter por `python-json-logger` para emitir JSON — facilita ingestão no Datadog/CloudWatch |
| Secrets management | Integrar com Railway Variables ou AWS Secrets Manager em vez de `.env` em produção |

---

## Fase 2 — Camada de dados e ML

### O que foi feito
- `app/ml/feature_engineering.py`: transformer sklearn-compatível (`HousePriceFeatureEngineer`) que cria 8 features derivadas
- `app/ml/preprocess.py`: carregamento, limpeza, merge com demographics, `ColumnTransformer`
- `app/ml/train.py`: pipeline completo com baseline (Ridge) e modelo final (XGBoost)
- `app/ml/evaluate.py`: métricas de regressão com dataclass `RegressionMetrics`
- `app/ml/model_registry.py`: toda a persistência centralizada em um módulo
- Log transform no target (`log1p`) para distribuição mais simétrica

### Resultados obtidos

| Modelo | RMSE | MAE | R² | MAPE |
|---|---|---|---|---|
| Ridge (baseline) | $184k | $108k | 0.764 | 19.7% |
| XGBoost final | $126k | $62k | **0.891** | 11.2% |

O XGBoost superou o baseline em **+42.6% de MAE** e **+0.127 de R²**.

### Por que foi feito assim
- **Transformer sklearn**: garante que feature engineering idêntico seja aplicado em treino e inferência — zero risco de vazamento de dados
- **OrdinalEncoder no zipcode**: evita explodir dimensionalidade com OneHotEncoder (~70 zipcodes únicos). Modelos de árvore lidam bem com ordinais
- **Log transform no preço**: distribuição de preços é assimétrica à direita (skewness ≈ 4). Log1p reduz para ~0.4 e melhora estabilidade do gradiente
- **Estratificação por faixa de preço no split**: garante distribuição balanceada de imóveis caros e baratos em treino e teste
- **SHAP para importância**: mais confiável que `feature_importances_` nativo para interpretar contribuições individuais
- **Medianas por zipcode salvas nos metadados**: calculadas apenas no treino (sem vazamento) e reutilizadas em inferência para contexto de mercado

### O que pode melhorar

| Melhoria | Como implementar |
|---|---|
| **Split temporal** | Em vez de split aleatório, treinar em Jan–Dez/2014 e testar em Jan–Mai/2015 — mais realista para produção |
| **Target encoding para zipcode** | `category_encoders.TargetEncoder` com cross-validation interna — melhor que ordinal para capturar valor real por zipcode |
| **Otimização de hiperparâmetros** | `Optuna` com `XGBRegressor` e validação cruzada temporal (TimeSeriesSplit) |
| **Intervalos de confiança** | `MapieRegressor` (conformal prediction) ou XGBoost com quantile regression para retornar `[p10, p50, p90]` |
| **Feature store** | Separar features computadas offline (medianas de zipcode, estatísticas de vizinhança) de features computadas online |
| **Detecção de drift** | `Evidently AI` ou `nannyml` para monitorar drift de features em produção |
| **Modelo ensemble** | Stacking de XGBoost + LightGBM + CatBoost com meta-learner Ridge |
| **Remover overfitting** | Gap treino/teste R² = 0.083. Reduzir `max_depth` para 5, aumentar `min_child_weight` para 5, adicionar mais regularização |

---

## Fase 3 — Inferência

### O que foi feito
- `app/api/schemas/prediction.py`: schema Pydantic completo com 18 campos, validadores e limites realistas
- `app/api/services/prediction_service.py`: orquestrador entre API e núcleo ML
- Enriquecimento automático com mediana do zipcode e desvio percentual
- `PredictionResult` dataclass como contrato interno entre ML e API
- `@lru_cache` nos artefatos para carregar uma vez e reutilizar

### Por que foi feito assim
- **Schema Pydantic separado do modelo ML**: a API pode evoluir sem tocar no ML (e vice-versa)
- **`to_model_input()`**: conversão explícita de schema para dict — nenhum dado entra no modelo sem passar por validação
- **`@lru_cache` nos artefatos**: evita re-leitura de disco (200ms+ por joblib.load) a cada requisição
- **`artifacts_exist()` antes de qualquer inferência**: falha rápida com mensagem clara em vez de `KeyError` opaco

### O que pode melhorar

| Melhoria | Como implementar |
|---|---|
| **Cache de predições** | Redis com TTL de 1h para inputs idênticos (hash do dict de input como chave) |
| **Versioning de modelo** | Adicionar `model_id` no schema de resposta e suportar múltiplas versões simultâneas via `model_registry.py` |
| **Schema versionado** | Prefixar endpoints com `/v1/predict`, `/v2/predict` para compatibilidade futura |
| **Validação de distribuição** | Verificar se o input está dentro do range do treino e retornar warning se for extrapolação |
| **Batch assíncrono** | Para lotes grandes, usar `asyncio` + `ThreadPoolExecutor` para paralelizar inferência |

---

## Fase 4 — Knowledge Base + RAG

### O que foi feito
- 5 documentos da knowledge base:
  - `business_context.md`: mercado KC, fatores de preço, segmentos
  - `feature_dictionary.md`: cada feature explicada com impacto no preço
  - `model_limitations.md`: honesto sobre escopo, dados históricos, outliers
  - `eda_summary.md`: estatísticas-chave, top zipcodes, correlações
  - `zipcode_insights.csv`: 60+ zipcodes com preço mediano, tier, grade médio, notas
- `app/rag/embeddings.py`: suporte dual OpenAI / fastembed (local, gratuito)
- `app/rag/build_kb.py`: ingestão com chunking diferenciado (Markdown vs CSV)
- `app/rag/retriever.py`: três funções especializadas de retrieval
- `app/rag/prompt_builder.py`: montagem de prompts com hierarquia clara

### Por que foi feito assim
- **fastembed como padrão**: ONNX-based, sem PyTorch, sem problema de path longo no Windows, gratuito. OpenAI como opção premium via `EMBEDDING_PROVIDER`
- **CSV linha a linha como documento**: evita misturar informações de zipcodes distintos num mesmo chunk — cada zipcode é recuperável individualmente
- **Chunk size 600 / overlap 80**: preserva contexto sem ultrapassar janela de embedding. Overlap evita cortes no meio de explicações importantes
- **`retrieve_for_prediction` vs `retrieve_for_chat`**: queries diferentes para contextos diferentes — a query de predição é enriquecida com faixa de preço e grade para melhor recall
- **Garantia de chunk de zipcode**: se nenhum chunk de zipcode aparecer nos top-k, o retriever faz uma busca específica para aquele zipcode — evita respostas genéricas

### O que pode melhorar

| Melhoria | Como implementar |
|---|---|
| **Reranking** | `FlashRank` ou `Cohere Rerank` após recuperação inicial para reordenar chunks por relevância semântica real |
| **Chunks hierárquicos** | `LlamaIndex` com `HierarchicalNodeParser` — indexa parágrafos E seções, recupera pelo nível certo |
| **Atualização incremental da KB** | Detectar mudanças nos arquivos e reindexar apenas os chunks afetados |
| **Avaliação do RAG** | `RAGAs` para medir faithfulness, answer relevancy e context precision automaticamente |
| **KB dinâmica com dados reais** | Ingerir dados de mercado atualizados via API (Zillow, Redfin) periodicamente |
| **Embeddings por domínio** | Fine-tunar `bge-small` no vocabulário imobiliário do KC para melhor qualidade de retrieval |
| **Metadata filtering** | Filtrar chunks por tipo (`type=zipcode`) antes da busca semântica quando a pergunta é sobre localização |

---

## Fase 5 — API FastAPI

### O que foi feito
- `app/api/main.py`: lifespan com verificação de componentes, CORS, exception handlers globais
- `GET /health`: status granular de cada componente (ML, RAG, LLM)
- `POST /predict`: predição pura sem LLM
- `POST /predict/explain`: predição + explicação automática
- `POST /predict/batch`: predição em lote (até 100)
- `POST /chat`: chat contextual com histórico
- `POST /chat/explain`: explicação inicial para predição existente
- Fallback gracioso no LLM: API funciona sem OpenAI (degraded mode)

### Por que foi feito assim
- **Separação predict / predict/explain**: quem não precisa do LLM paga apenas o custo do ML (< 50ms). Quem quer explicação opta explicitamente
- **Stateless por design**: o contexto da predição é enviado pelo cliente em cada request do chat — API não mantém estado de sessão, escala horizontalmente sem Redis
- **Exception handlers globais**: `FileNotFoundError` vira 503, `ValueError` vira 422 — erros previsíveis com mensagens claras ao invés de 500 genérico
- **Lifespan ao invés de `@app.on_event`**: API recomendada pelo FastAPI desde 0.93. Garante cleanup no shutdown

### O que pode melhorar

| Melhoria | Como implementar |
|---|---|
| **Autenticação** | `FastAPI Security` com API Keys em header ou JWT Bearer tokens |
| **Rate limiting** | `slowapi` (wrapper do `limits` para FastAPI) por IP e por API key |
| **Streaming no chat** | `StreamingResponse` com `openai.stream=True` para resposta token a token |
| **Cache de chat** | Cachear respostas idênticas com `aiocache` + Redis (hash da pergunta + contexto como chave) |
| **Observabilidade** | `OpenTelemetry` + traces no Datadog ou Grafana para medir latência por etapa |
| **Testes de integração** | `pytest` + `httpx.AsyncClient` para testar os endpoints com artefatos reais em CI |
| **OpenAPI customizado** | Adicionar exemplos reais nos schemas para gerar documentação mais rica no Swagger |
| **Compressão** | `GZipMiddleware` do FastAPI para responses grandes (batch predictions) |

---

## Fase 6 — Interface Streamlit

### O que foi feito
- Sidebar com formulário completo: zipcode (selectbox com 27 bairros KC), quartos, banheiros, área, grade, condição, vista, waterfront
- Coordenadas lat/long preenchidas automaticamente pelo zipcode
- Card de preço com gradient e desvio % vs. mediana do zipcode
- Métricas resumidas em linha (quartos, banheiros, área, grade)
- Gráfico horizontal de feature importance (SHAP)
- Explicação AI automática após predição
- Chat com histórico persistido em session state
- Tela de boas-vindas quando não há predição ativa

### Por que foi feito assim
- **Nenhuma lógica ML/RAG na UI**: Streamlit consome apenas a API via `requests`. Toda a inteligência fica nos serviços
- **Session state para histórico de chat**: evita re-renderizações desnecessárias e mantém contexto entre turnos
- **Selectbox de zipcode com nome**: UX muito melhor que digitar "98103" sem saber o que significa
- **CSS inline para o card de preço**: Streamlit tem limitações de estilo nativo. CSS inline permite o visual premium sem deps externas

### O que pode melhorar

| Melhoria | Como implementar |
|---|---|
| **Mapa interativo do imóvel** | `st.map()` ou `pydeck` com o pin na coordenada lat/long do zipcode selecionado |
| **Comparador de imóveis** | Permitir salvar múltiplas predições e exibir tabela comparativa lado a lado |
| **Gauge de confiança** | `plotly` com gauge chart indicando nível de confiança baseado no MAPE do zipcode |
| **Inputs validados em tempo real** | `streamlit-pydantic` para renderizar o `HouseInput` automaticamente com validação Pydantic |
| **Streaming no chat** | `st.write_stream()` (Streamlit 1.32+) com a API retornando `StreamingResponse` |
| **Histórico de sessões** | Salvar predições anteriores em `localStorage` via `streamlit-local-storage` |
| **Dark/light mode** | Configurar `[theme]` no `.streamlit/config.toml` |
| **Autenticação básica** | `streamlit-authenticator` para proteger a interface em produção |

---

## Configurações resolvidas durante o desenvolvimento

| Problema encontrado | Causa | Solução aplicada |
|---|---|---|
| `ModuleNotFoundError: langchain` | Dependências não instaladas | `pip install -r requirements.txt` |
| `openai.RateLimitError: insufficient_quota` | Conta OpenAI sem créditos | Implementado fallback com `fastembed` (ONNX local, gratuito) |
| `OSError: path too long` (sentence-transformers) | Windows Long Path desabilitado, sem admin | Substituído por `fastembed` que usa caminhos mais curtos |
| Pillow incompatível com Streamlit | `fastembed` instalou `pillow 12` | `pip install "pillow<11"` |
| Porta 8000 ocupada por nginx | Outro serviço rodando na porta | API movida para porta 8001 |
| `UnicodeEncodeError: charmap` (✓ no log) | Console Windows (cp1252) não suporta `✓` | Substituído por texto ASCII simples |
| Pydantic warning `model_path` / `model_version` | Namespace protegido `model_` | `protected_namespaces=()` no `model_config` |

---

## Próximos passos prioritários

### Curto prazo (melhorias imediatas)

1. **Reduzir overfitting do XGBoost**
   - Reduzir `max_depth` de 6 para 5
   - Aumentar `min_child_weight` de 3 para 5
   - Adicionar `early_stopping_rounds` com conjunto de validação

2. **Adicionar testes automatizados**
   ```
   tests/
   ├── test_preprocess.py   ← testar feature engineering
   ├── test_predict.py      ← testar inferência com artefatos reais
   ├── test_rag.py          ← testar retrieval (mocked embeddings)
   └── test_api.py          ← testar endpoints com httpx
   ```

3. **Streaming no chat**
   - `openai.stream=True` na API
   - `st.write_stream()` na UI

4. **Mapa interativo**
   - `pydeck` com pin no zipcode selecionado

### Médio prazo

5. **Target encoding para zipcode** — melhora R² estimado em 1–2%
6. **Intervalos de confiança** com conformal prediction (`MapieRegressor`)
7. **Pipeline de retreino automático** com Airflow ou GitHub Actions
8. **Autenticação da API** com API Keys

### Longo prazo (para escalar o produto)

9. **Model registry completo** com MLflow — versioning, comparison, rollback
10. **Feature store** com Feast ou Hopsworks
11. **Monitoramento de drift** com Evidently AI
12. **Multi-região** — expandir dataset para outros condados de WA

---

## Estrutura final do repositório

```
madeinweb-teste/
├── app/
│   ├── api/
│   │   ├── main.py                        ← FastAPI app, CORS, lifespan
│   │   ├── routes/
│   │   │   ├── health.py                  ← GET /health
│   │   │   ├── predict.py                 ← POST /predict, /predict/explain, /predict/batch
│   │   │   └── chat.py                    ← POST /chat, /chat/explain
│   │   ├── schemas/
│   │   │   ├── prediction.py              ← HouseInput, PredictionResponse, BatchPrediction*
│   │   │   └── chat.py                    ← ChatRequest, ChatResponse, PredictionContext
│   │   └── services/
│   │       ├── prediction_service.py      ← ML → PredictionResponse + context
│   │       ├── explanation_service.py     ← ML + RAG + LLM → explicação
│   │       ├── rag_service.py             ← wraps retriever para a API
│   │       └── llm_service.py             ← chamada OpenAI + fallback gracioso
│   │
│   ├── ml/
│   │   ├── feature_engineering.py         ← HousePriceFeatureEngineer (sklearn transformer)
│   │   ├── preprocess.py                  ← load, clean, merge, ColumnTransformer
│   │   ├── train.py                       ← pipeline completo Ridge + XGBoost
│   │   ├── evaluate.py                    ← RegressionMetrics, SHAP importance
│   │   ├── predict.py                     ← predict_price(), predict_batch(), PredictionResult
│   │   └── model_registry.py              ← save/load artefatos (modelo, preprocessor, metadata)
│   │
│   ├── rag/
│   │   ├── embeddings.py                  ← fastembed (local) ou OpenAI (premium)
│   │   ├── build_kb.py                    ← ingestão Markdown + CSV → FAISS
│   │   ├── retriever.py                   ← retrieve(), retrieve_for_prediction(), retrieve_for_chat()
│   │   └── prompt_builder.py              ← montagem de prompts com contexto estruturado
│   │
│   ├── ui/
│   │   └── streamlit_app.py               ← interface completa (consome API via requests)
│   │
│   └── core/
│       ├── config.py                      ← Settings (pydantic-settings) + singleton
│       ├── logger.py                      ← logger centralizado por módulo
│       └── utils.py                       ← funções utilitárias sem estado
│
├── data/
│   ├── raw/
│   │   └── kc_house_data.csv              ← dataset King County (Kaggle)
│   └── knowledge_base/
│       ├── business_context.md
│       ├── feature_dictionary.md
│       ├── model_limitations.md
│       ├── eda_summary.md
│       └── zipcode_insights.csv
│
├── artifacts/
│   ├── model/
│   │   ├── house_price_model.joblib       ← XGBoost Pipeline (gerado por make train)
│   │   ├── preprocessor.joblib            ← ColumnTransformer + FeatureEngineer
│   │   └── metadata.json                  ← métricas, features, importância, medianas zipcode
│   └── vectorstore/                       ← índice FAISS (gerado por make build-kb)
│
├── .env                                   ← configurações locais (não versionar)
├── .env.example                           ← template de configuração
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── projeto.md                             ← este arquivo
```

---

## Como rodar localmente (resumo)

```powershell
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com sua OPENAI_API_KEY (opcional, mas necessário para chat)

# 3. Colocar kc_house_data.csv em data/raw/ (Kaggle)

# 4. Treinar o modelo
python -m app.ml.train

# 5. Construir a knowledge base
python -m app.rag.build_kb

# 6. Subir a API (Terminal 1)
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8001 --reload

# 7. Subir a UI (Terminal 2)
python -m streamlit run app/ui/streamlit_app.py --server.port 8501
```

**Acessar:**
- UI: http://localhost:8501
- API docs: http://localhost:8001/docs
- Health: http://localhost:8001/health
