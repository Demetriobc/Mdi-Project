# Artefatos de Resultado

Esta pasta contém os artefatos de saída do projeto — métricas, importâncias de features e predições em dados novos. Todos os valores são gerados diretamente pelo código do projeto, não editados manualmente.

---

## `metrics_summary.csv`

**O que é:** comparação de performance entre o modelo baseline (Ridge) e o modelo final (XGBoost), avaliados separadamente em treino e teste.

**Colunas:**

| Coluna | Descrição |
|---|---|
| `model` | Nome do modelo (`Ridge` ou `XGBoost`) |
| `split` | Partição avaliada (`train` ou `test`) |
| `rmse` | Root Mean Squared Error em dólares |
| `mae` | Mean Absolute Error em dólares |
| `r2` | Coeficiente de determinação (0–1) |
| `mape` | Mean Absolute Percentage Error em % |
| `median_ae` | Mediana do erro absoluto em dólares — mais robusta que MAE na presença de outliers |
| `n_samples` | Número de amostras na partição |

**O que contar com este arquivo:**
- O XGBoost reduz o MAE em **43%** (de US$ 108k para US$ 62k) em relação ao Ridge no teste
- O gap de R² treino–teste do XGBoost (0.974 → 0.891 = 0.083) é aceitável para um dataset com alta variação geográfica
- O Ridge tem performance quase idêntica em treino e teste (R² 0.743 vs 0.764) — sem overfitting, mas também sem captura de não-linearidades

**Como gerar:** `make train` — as métricas são calculadas automaticamente e salvas em `artifacts/model/metadata.json`.

---

## `feature_importance.csv`

**O que é:** importância de cada feature calculada por dois métodos distintos — gain do XGBoost e SHAP values — com rankings e descrições.

**Colunas:**

| Coluna | Descrição |
|---|---|
| `feature` | Nome da feature |
| `importance_gain` | Importância pelo método gain (contribuição para redução da função de perda nas divisões) |
| `rank_gain` | Ranking pelo gain (1 = mais importante) |
| `importance_shap` | Importância pelo valor SHAP médio absoluto no conjunto de teste |
| `rank_shap` | Ranking pelo SHAP (1 = mais importante) |
| `description` | Descrição da feature e interpretação |

**O que contar com este arquivo:**

A divergência entre os dois rankings é a parte mais informativa:

- **`grade`**: 1º no gain, 3º no SHAP — é usado em muitas divisões (alto gain), mas o impacto marginal médio por imóvel é menor do que o de `lat`
- **`lat`**: 3º no gain, **1º no SHAP** — a latitude tem o maior impacto marginal médio por observação; captura micro-localização dentro do condado
- **`waterfront`**: 4º no gain, 20º no SHAP — divisão muito informativa quando presente (alto gain), mas afeta apenas 0,75% dos imóveis (baixo SHAP médio)
- **`sale_month`**: não entra no top-20 de gain, mas é 11º no SHAP — o modelo aprende sazonalidade de forma distribuída entre as árvores

Para comunicação com stakeholders, usar o **ranking SHAP** — ele responde "quais fatores mais movem o preço de um imóvel típico".

**Como gerar:** `make train` — calculado automaticamente durante o treinamento.

---

## `future_predictions.csv`

**O que é:** predições do modelo XGBoost para 100 imóveis do arquivo `data/raw/future_unseen_examples.csv` — dados que nunca foram vistos durante o treinamento.

**Colunas:**

| Coluna | Descrição |
|---|---|
| `id` | Identificador sequencial do imóvel |
| `zipcode` | Código postal em King County |
| `grade` | Qualidade construtiva (1–13) |
| `sqft_living` | Área útil interior em sqft |
| `bedrooms` | Número de quartos |
| `bathrooms` | Número de banheiros |
| `condition` | Condição do imóvel (1–5) |
| `waterfront` | Frente para a água (0/1) |
| `view` | Qualidade da vista (0–4) |
| `predicted_price` | Estimativa central do modelo (p50) em US$ |
| `p10` | Limite inferior do intervalo de confiança (percentil 10) em US$ |
| `p90` | Limite superior do intervalo de confiança (percentil 90) em US$ |
| `interval_width` | Largura do intervalo P10–P90 em US$ |

**O que contar com este arquivo:**

- **Amplitude de previsão:** de US$ 162.020 (imóvel grade 6, 880 sqft, Kent/98042) até US$ 2.093.563 (grade 10, 4.580 sqft, waterfront, Sammamish/98075) — o modelo generaliza bem em toda a faixa de mercado
- **Intervalo proporcional ao preço:** imóveis mais caros têm intervalos mais largos em termos absolutos, mas proporcionalmente similares — isso é esperado e correto
- **Caso extremo (id=51):** único imóvel waterfront do conjunto, grade 10, view=4, em 98075 — estimativa de US$ 2.09M com intervalo de US$ 837k. Intervalo largo reflete corretamente a maior incerteza nesse segmento
- **Imóveis de entrada (grade 6, zipcode periférico):** estimativas coerentes com o mercado real de Auburn/Kent (US$ 160k–270k)

**Como gerar:**
```python
import numpy as np, pandas as pd, joblib
model = joblib.load("artifacts/model/house_price_model.joblib")
df = pd.read_csv("data/raw/future_unseen_examples.csv")
df["date"] = "20150601"
pred = np.expm1(model.predict(df))
```

---

## Reprodutibilidade

Todos os arquivos desta pasta podem ser regenerados a partir do código do projeto:

```bash
make train        # regenera metrics_summary (via metadata.json)
python -m app.ml.predict   # regenera future_predictions
```

Os valores são determinísticos — `random_state=42` está fixado em todos os componentes do pipeline.
