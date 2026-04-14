# Decisões de Modelagem

---

## 1. Objetivo e Métrica Principal

**Objetivo:** prever o preço de venda de imóveis residenciais em King County, WA, com o menor erro absoluto possível em escala monetária.

**Métricas de avaliação:**

| Métrica | Por que usar |
|---|---|
| **MAE** | Erro médio em dólares — diretamente interpretável para negócio |
| **RMSE** | Penaliza erros grandes — importante para evitar estimativas muito distantes em imóveis de alto valor |
| **R²** | Proporção da variância explicada pelo modelo — permite comparação entre modelos |
| **MAPE** | Erro percentual médio — comparação entre imóveis de faixas de preço diferentes |
| **Median AE** | Mais robusto que MAE na presença de outliers |

---

## 2. Estratégia de Split

O split entre treino e teste foi feito de forma **temporal**, não aleatória.

- **Treino:** vendas anteriores a 01/01/2015 — 17.148 registros
- **Teste:** vendas a partir de 01/01/2015 — 4.287 registros

**Racional:** um split aleatório permitiria que o modelo aprendesse padrões de imóveis "futuros" no treino, inflando artificialmente as métricas. O split temporal simula o cenário real: treinar com o passado e avaliar em dados que ainda não existiam no momento do treino. É a forma mais honesta de estimar performance em produção.

**Implicação:** as métricas reportadas são mais conservadoras do que seriam com split aleatório, mas mais realistas.

---

## 3. Modelos Avaliados

### 3.1 Ridge (baseline)

Regressão linear com regularização L2 (alpha = 10.0). Treinada sobre as features após transformação logarítmica do target.

**Por que foi incluído:**  
Um baseline linear bem feito é mais valioso do que qualquer modelo complexo sem ponto de comparação. O Ridge estabelece o teto de performance de uma abordagem linear e justifica a adoção de um modelo mais sofisticado.

**Resultados no teste:**

| Métrica | Ridge |
|---|---|
| RMSE | US$ 184.856 |
| MAE | US$ 108.237 |
| R² | 0.764 |
| MAPE | 19.66% |

### 3.2 XGBoost (modelo final)

Gradient boosting com árvores de decisão. Vantagens para este problema:

- **Captura não-linearidades** — o efeito de `grade` não é linear; o salto de valor entre grades não é constante
- **Interações entre features** — o impacto de `sqft_living` depende do `zipcode`; árvores capturam isso naturalmente
- **Robustez a outliers** — menos sensível a imóveis atípicos do que modelos lineares
- **Sem necessidade de normalização** — variáveis em escalas diferentes não prejudicam o modelo
- **Importância interpretável** — gain e SHAP disponíveis nativamente

**Hiperparâmetros:**

```python
{
    "n_estimators": 600,         # máximo; early stopping determina o valor real
    "max_depth": 6,              # árvores rasas reduzem overfitting
    "learning_rate": 0.05,       # taxa conservadora com muitas árvores
    "subsample": 0.8,            # amostragem de linhas por árvore
    "colsample_bytree": 0.8,     # amostragem de features por árvore
    "min_child_weight": 3,       # mínimo de amostras por folha
    "reg_alpha": 0.1,            # regularização L1
    "reg_lambda": 1.0,           # regularização L2
    "tree_method": "hist",       # método eficiente para datasets grandes
}
```

---

## 4. Decisões Técnicas

### 4.1 Transformação log1p no target

O preço tem distribuição assimétrica (skewness ≈ 4.0). Treinar diretamente em dólares faz com que a função de perda seja dominada por imóveis de alto valor. A transformação `log1p` comprime a escala, tratando erros percentuais de forma mais uniforme em toda a distribuição.

A reconversão em inferência é feita com `expm1` para garantir que a previsão final está em dólares.

### 4.2 Early stopping via holdout interno

Para determinar o `n_estimators` ideal sem overfitting, 10% do conjunto de treino é separado como validação interna. O XGBoost monitora o RMSE nesse holdout a cada árvore adicionada e para quando a melhoria não ocorre por 50 rounds consecutivos. O `n_estimators` final é o melhor ponto encontrado.

Isso evita tanto underfitting (poucas árvores) quanto overfitting (árvores em excesso), sem necessidade de cross-validation completo.

### 4.3 Quantile Regression (P10 e P90)

Além do modelo de ponto central (p50), dois modelos adicionais foram treinados com `objective="reg:quantileerror"`:

- **p10:** estima o 10º percentil — piso provável da estimativa
- **p90:** estima o 90º percentil — teto provável da estimativa

O intervalo [P10, P90] captura o preço real em **~80%** dos casos no conjunto de teste, com largura média de aproximadamente US$ 194.000. Isso transforma a previsão de um número único em uma faixa defensável, o que é muito mais útil para qualquer decisão de negócio.

### 4.4 Pipeline scikit-learn

O pré-processamento e o modelo foram empacotados em um `Pipeline` do scikit-learn, com um `TransformerMixin` customizado (`DerivedHousingFeatures`) que aplica o feature engineering. Isso garante:

- O mesmo código roda em treino e inferência sem risco de divergir
- O preprocessador salvo em `artifacts/model/preprocessor.joblib` é stateful e reproduzível
- Não há vazamento de informação do teste para o treino

---

## 5. Resultados Finais

Avaliação no conjunto de teste (4.287 registros, jan–mai 2015):

| Métrica | Ridge (baseline) | XGBoost Final | Diferença |
|---|---|---|---|
| RMSE | US$ 184.856 | US$ 125.845 | −32% |
| MAE | US$ 108.237 | US$ 62.083 | −43% |
| R² | 0.764 | **0.891** | +17pp |
| MAPE | 19.66% | **11.24%** | −8pp |
| Median AE | US$ 67.751 | US$ 34.330 | −49% |

**Gap treino-teste (R²):** 0.083 (treino R² = 0.974 → teste R² = 0.891).

Um gap de 0.083 em R² é esperado para um dataset com variação geográfica alta e alguns segmentos sub-representados (waterfront, luxo). Não há sinal de overfitting expressivo — o modelo não está memorizando o treino; está generalizando com degradação esperada para dados fora do período de treino.

---

## 6. Importância de Variáveis

Duas métricas de importância foram calculadas:

**Gain (XGBoost nativo):** mede a contribuição média de uma feature para reduzir a função de perda nas divisões das árvores.

**SHAP (Shapley values):** mede o impacto marginal médio de uma feature no valor da previsão para cada observação do conjunto de teste.

| Feature | Gain | SHAP | Divergência |
|---|---|---|---|
| `grade` | **1º (43.3%)** | 3º (9.7%) | Grade aparece em muitas divisões, mas o impacto marginal médio por observação é menor do que o da lat |
| `sqft_living` | 2º (15.1%) | 2º (12.7%) | Consistente nas duas métricas |
| `lat` | 3º (11.9%) | **1º (23.6%)** | Latitude tem impacto marginal alto por observação — captura micro-localização dentro do zipcode |
| `waterfront` | 4º (5.7%) | 10º+ (0.4%) | Flag binária: aparece em poucas observações mas com divisão de alto ganho quando presente |
| `view` | 5º (4.5%) | 9º (2.1%) | Similar ao waterfront — impacto concentrado em poucos casos |
| `long` | 9º (1.8%) | 4º (4.7%) | Longitude captura gradiente leste-oeste (Eastside vs subúrbios sul) |

**Interpretação da divergência gain vs SHAP:**

A divergência é esperada e informativa. Gain reflete o quanto cada feature reduz o erro durante o treino — features binárias raras (waterfront) aparecem em poucos splits mas cada split é muito informativo. SHAP mede o impacto por observação — features com alta variância contínua (lat, sqft_living) aparecem em mais observações com impacto médio alto.

Para decisões de negócio, **SHAP é mais interpretável**: lat, sqft_living e grade são os três fatores que mais movem o preço para um imóvel qualquer.

---

## 7. Limitações Técnicas

**Dados históricos (2014–2015):** as estimativas refletem o nível de preços daquele período. Para uso em contexto atual, os valores precisariam ser ajustados por um índice de valorização.

**Extrapolação geográfica:** o modelo é válido apenas para zipcodes de King County. Coordenadas fora do range [47.15, 47.78] em latitude produzem previsões sem sentido.

**Imóveis atípicos:** para waterfront, grade ≥ 11 e preços acima de US$ 2M, o modelo tem menos dados de treino e a margem de erro é maior. A quantile regression mitiga parcialmente esse problema ao gerar intervalos mais largos nesses casos.

**Multicolinearidade:** `sqft_living`, `sqft_above` e `sqft_living15` são correlacionados. Em XGBoost, isso não causa instabilidade de coeficientes como em modelos lineares, mas dificulta a interpretação isolada de cada feature. As importâncias devem ser lidas em conjunto, não individualmente.

**Sem dados macroeconômicos:** taxa de juros, inflação e oferta de mercado não estão no modelo. Mudanças abruptas de cenário econômico não são capturadas.

---

## 8. Caminhos Futuros

**Conformal prediction:** substituir ou complementar a quantile regression por conformal prediction para intervalos de confiança com cobertura garantida calibrada estatisticamente.

**Embeddings geográficos:** representar zipcode com embeddings treinados ao invés de encoding ordinal pode melhorar a captura de similaridade entre bairros adjacentes.

**Ensemble com modelo geográfico:** adicionar um modelo de interpolação espacial (kriging ou vizinhos mais próximos) como feature de entrada pode capturar variações locais finas que o zipcode não resolve.

**Reentreino com dados mais recentes:** a melhoria mais imediata em valor de negócio seria incorporar transações de 2020–2024 para refletir o mercado atual de Seattle.

---

*Código de treinamento: [`app/ml/train.py`](../app/ml/train.py) | Artefatos: [`artifacts/model/metadata.json`](../artifacts/model/metadata.json)*
