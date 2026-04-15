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

### Por que split temporal e não aleatório?

Em problemas com séries temporais ou dados com data de transação, o split aleatório quebra a ordem causal dos dados. No contexto imobiliário:

- **Leakage temporal:** com split aleatório, o modelo veria no treino imóveis vendidos em março/2015 enquanto tenta prever um imóvel vendido em janeiro/2015. Na prática, isso não é possível — no momento da previsão, dados futuros ainda não existem.
- **Inflação artificial de métricas:** split aleatório permitiria que o modelo "aprendesse" padrões de mercado de 2015 ao tentar prever vendas de 2014. As métricas reportadas pareceriam melhores mas não refletiriam a performance real em produção.
- **Simulação realista:** o split temporal imita o cenário de produção — treinar com o que se sabe até hoje e avaliar no que acontece depois. É a única forma honesta de estimar a performance futura do modelo.

**Implicação prática:** as métricas reportadas são mais conservadoras do que com split aleatório (o modelo não "viu o futuro"), mas são também mais realistas e não enganam stakeholders sobre a capacidade real do sistema.

**Verificação de representatividade:** a distribuição de preços entre treino e teste foi verificada — preço médio treino: US$ 530k vs. teste: US$ 560k. A pequena diferença é esperada (mercado de Seattle aquece no início do ano) e não invalida a avaliação.

---

## 3. Modelos Avaliados

### 3.1 Ridge (baseline)

Regressão linear com regularização L2 (alpha = 10.0). Treinada sobre as features após transformação logarítmica do target.

**Por que foi incluído:**  
Um baseline linear bem feito é mais valioso do que qualquer modelo complexo sem ponto de comparação. O Ridge estabelece o teto de performance de uma abordagem linear e justifica a adoção de um modelo mais sofisticado — sem ele, não há como afirmar que a complexidade adicional do XGBoost valeu a pena.

**Resultados no teste:**

| Métrica | Ridge |
|---|---|
| RMSE | US$ 184.856 |
| MAE | US$ 108.237 |
| R² | 0.764 |
| MAPE | 19.66% |

### 3.2 XGBoost (modelo final)

Gradient boosting com árvores de decisão. Escolhido após análise do problema e comparação com o baseline.

#### Por que XGBoost e não outros algoritmos?

| Alternativa considerada | Por que não foi escolhida |
|---|---|
| **Regressão linear (Ridge)** | Assume linearidade — o efeito de `grade`, `waterfront` e `lat` não é linear. O Ridge ficou 43% pior em MAE. |
| **Random Forest** | Também captura não-linearidades, mas tende a ser superado por gradient boosting em tabular data. XGBoost tem regularização embutida (L1/L2) e early stopping nativos que controlam overfitting com mais precisão. |
| **LightGBM** | Performance comparável ao XGBoost no dataset; escolhemos XGBoost pela maturidade da API, melhor suporte a `quantile_alpha` para regressão quantílica, e ecossistema de SHAP mais estável. |
| **Redes neurais (MLP)** | Com ~17k registros tabulares, redes neurais raramente superam gradient boosting e exigem normalização, tuning de arquitetura e muito mais tempo de treino. O ganho esperado não justificaria a complexidade adicional. |

**Vantagens específicas do XGBoost para este problema:**

- **Captura não-linearidades nativas:** o efeito de `grade` não é linear (cada ponto adicional vale mais que o anterior); o impacto de `sqft_living` depende do `zipcode`. Árvores modelam essas interações sem feature engineering adicional.
- **Interações entre variáveis:** um imóvel com alta área em Bellevue vale muito mais do que a soma dos efeitos isolados de área e localização. XGBoost captura essa interação na estrutura das árvores.
- **Robusto a outliers:** imóveis atípicos (waterfront > US$ 3M, grade 13) influenciam menos o XGBoost do que um modelo linear, porque as árvores os isolam em folhas específicas em vez de distorcer os coeficientes globais.
- **Sem necessidade de normalização das features:** `sqft_living` (em milhares) e `lat` (em unidades decimais) ficam na mesma árvore sem prejudicar o aprendizado — ao contrário do Ridge, que exige `StandardScaler`.
- **Importância interpretável:** gain e SHAP values são nativos ao XGBoost, o que facilita a explicação de previsões ao usuário final via assistente conversacional.

**Hiperparâmetros do modelo final:**

```python
{
    "n_estimators": 600,          # máximo; early stopping determina o valor real usado
    "max_depth": 5,               # árvores rasas — controlam overfitting sem perder capacidade
    "learning_rate": 0.05,        # taxa conservadora; trabalha junto com muitas árvores
    "subsample": 0.8,             # 80% das linhas por árvore — reduz variância
    "colsample_bytree": 0.8,      # 80% das features por árvore — reduz correlação entre árvores
    "min_child_weight": 5,        # mínimo de "peso" de amostras por folha — evita folhas com poucos dados
    "reg_alpha": 0.1,             # regularização L1 (lasso) — sparsidade nos pesos
    "reg_lambda": 1.5,            # regularização L2 (ridge) — suaviza os pesos
    "tree_method": "hist",        # histograma de features — eficiente para datasets de médio porte
    "random_state": 42,           # reprodutibilidade
}
```

**Racional dos hiperparâmetros críticos:**

- `max_depth=5` (não 6 ou 7): árvores mais rasas forçam o modelo a distribuir o aprendizado entre mais árvores em vez de criar árvores profundas que memorizam casos específicos. Com `learning_rate=0.05` e `n_estimators` controlado por early stopping, essa combinação foi a mais equilibrada.
- `min_child_weight=5`: exige que cada folha tenha equivalente a pelo menos 5 observações de peso. Isso é especialmente importante para imóveis raros (waterfront, grade 11+) — sem esse controle, o modelo criaria folhas muito específicas para esses casos e não generalizaria.
- `reg_lambda=1.5`: regularização L2 mais forte que o padrão (1.0) para compensar a relativa pequenez do dataset (~17k registros de treino) e a alta dimensionalidade após encoding do zipcode.

---

## 4. Decisões Técnicas

### 4.1 Transformação log1p no target

O preço tem distribuição assimétrica (skewness ≈ 4.0). Treinar diretamente em dólares faz com que a função de perda seja dominada por imóveis de alto valor — um erro de US$ 300k em um imóvel de US$ 3M pesa 100x mais que o mesmo erro em um imóvel de US$ 300k, mesmo que em termos percentuais sejam equivalentes.

A transformação `log1p` comprime a escala e trata erros percentuais de forma mais uniforme em toda a distribuição. Após transformação, a skewness do target cai de ≈ 4.0 para ≈ 0.4.

A reconversão em inferência é feita com `expm1` para garantir que a previsão final está em dólares. Esse processo é encapsulado no pipeline scikit-learn e ocorre de forma transparente — o código de inferência não precisa conhecer a transformação.

**Efeito prático:** com `log1p`, o modelo trata um erro de US$ 50k em um imóvel de US$ 500k e um erro de US$ 100k em um imóvel de US$ 1M com peso similar (ambos ~10%), em vez de dar peso 4x maior ao segundo caso.

### 4.2 Early stopping via holdout interno

Para determinar o `n_estimators` ideal sem overfitting, 10% do conjunto de treino é separado como validação interna (holdout). O XGBoost monitora o RMSE nesse holdout a cada árvore adicionada e para automaticamente quando não há melhoria por 50 rounds consecutivos. O `n_estimators` final é o melhor ponto encontrado.

```
treino completo (17.148 registros)
  ├── 90% (15.433) → treina o XGBoost
  └── 10% (1.715) → monitora RMSE a cada árvore
                     → para quando 50 rounds sem melhoria
                     → best_iteration + 1 → n_estimators final
```

Isso evita tanto underfitting (poucas árvores) quanto overfitting (árvores em excesso), sem necessidade de cross-validation completo que seria lento e consumiria os dados de treino.

**Separação do holdout interno do conjunto de teste:** o holdout de 10% é retirado do treino e nunca toca o conjunto de teste. O teste final usa os 17.148 registros completos para treinar o modelo final com o `n_estimators` determinado pelo holdout.

### 4.3 Quantile Regression (P10 e P90)

Além do modelo de ponto central (p50), dois modelos adicionais foram treinados com `objective="reg:quantileerror"`:

- **p10 (`quantile_alpha=0.1`):** estima o 10º percentil — piso provável da estimativa. Em 90% dos casos, o preço real estará acima.
- **p90 (`quantile_alpha=0.9`):** estima o 90º percentil — teto provável da estimativa. Em 90% dos casos, o preço real estará abaixo.

O intervalo [P10, P90] captura o preço real em **~80%** dos casos no conjunto de teste, com largura média de aproximadamente US$ 194.000.

**Por que isso é melhor do que um único número:**
- Um avaliador imobiliário profissional nunca diz "este imóvel vale exatamente US$ 450.000" — ele diz "entre US$ 420k e US$ 490k". O intervalo P10–P90 é o equivalente quantitativo dessa prática.
- Para imóveis típicos (grade 7–9, sem waterfront), o intervalo é estreito (~US$ 130k). Para imóveis atípicos (waterfront, grade 11+), o intervalo é mais largo — comunicando ao usuário que há mais incerteza nesses casos.
- Para decisões de negócio (oferta de compra, financiamento), saber o piso e o teto é mais defensável do que um ponto único.

### 4.4 Pipeline scikit-learn

O pré-processamento e o modelo foram empacotados em um `Pipeline` do scikit-learn, com um `TransformerMixin` customizado (`DerivedHousingFeatures`) que aplica o feature engineering. Isso garante:

- O mesmo código roda em treino e inferência sem risco de divergir — o preprocessador é stateful e serializado junto com o modelo
- O `preprocessor.joblib` salvo em `artifacts/model/` é reproduzível — qualquer instância da API carrega exatamente o mesmo estado que foi usado no treino
- Não há vazamento de informação do teste para o treino — o `TargetEncoder` do zipcode é fitado exclusivamente nos dados de treino

```
Pipeline (treino e inferência idênticos):
  DerivedHousingFeatures      → cria as 8 features derivadas
  ColumnTransformer           → StandardScaler (numéricas) + TargetEncoder (zipcode)
  XGBRegressor                → previsão em log-espaço
                              → expm1 aplicado na saída → preço em USD
```

---

## 5. Resultados Finais

Avaliação no conjunto de teste (4.287 registros, jan–mai 2015):

| Métrica | Ridge (baseline) | XGBoost Final | Melhoria |
|---|---|---|---|
| RMSE | US$ 184.856 | US$ 125.845 | **−32%** |
| MAE | US$ 108.237 | US$ 62.083 | **−43%** |
| R² | 0.764 | **0.891** | +17pp |
| MAPE | 19.66% | **11.24%** | −8.4pp |
| Median AE | US$ 67.751 | US$ 34.330 | **−49%** |

**Gap treino-teste (R²):** 0.083 (treino R² = 0.974 → teste R² = 0.891).

Um gap de 0.083 em R² é esperado e aceitável para este dataset. Os fatores que contribuem para o gap são conhecidos e não indicam overfitting expressivo:
1. **Variação geográfica:** o conjunto de teste inclui períodos sazonalmente diferentes do treino
2. **Segmentos sub-representados:** waterfront e grade ≥ 11 têm poucos registros no treino — o modelo tem menos dados para calibrar esses casos
3. **Deriva temporal natural:** o mercado imobiliário de Seattle cresceu entre 2014 e 2015; o modelo não captura essa tendência de valorização

O modelo não está memorizando o treino — está generalizando com degradação esperada para dados fora do período de treino.

---

## 6. Importância de Variáveis

Duas métricas de importância foram calculadas:

**Gain (XGBoost nativo):** mede a contribuição média de cada feature para reduzir a função de perda nas divisões das árvores — reflete o impacto durante o treino.

**SHAP (Shapley values):** mede o impacto marginal médio de cada feature no valor da previsão para cada observação do conjunto de teste — reflete o impacto na inferência.

| Feature | Gain (rank) | Gain (%) | SHAP (rank) | SHAP (%) | Interpretação |
|---|---|---|---|---|---|
| `grade` | 1º | 43.3% | 3º | 9.7% | Aparece em muitas divisões (alto gain), mas impacto marginal médio por observação é menor que `lat` |
| `sqft_living` | 2º | 15.1% | 2º | 12.7% | Consistente nas duas métricas — variável mais estável em impacto |
| `lat` | 3º | 11.9% | **1º** | 23.6% | Captura micro-localização dentro do zipcode — impacto marginal alto por observação |
| `waterfront` | 4º | 5.7% | 10º+ | 0.4% | Flag binária rara: impacto enorme nos casos positivos, zero nos negativos — baixo SHAP médio |
| `view` | 5º | 4.5% | 9º | 2.1% | Similar ao waterfront — impacto concentrado em poucos casos (view 3 e 4) |
| `long` | 9º | 1.8% | 4º | 4.7% | Gradiente leste-oeste (Eastside vs. subúrbios sul) — captura variação não coberta pelo zipcode |

**Interpretação da divergência gain vs SHAP:**

A divergência é esperada e informativa. Gain reflete o impacto durante o treino — features binárias raras como `waterfront` aparecem em poucos splits, mas cada split é extremamente informativo (separa imóveis de US$ 440k de imóveis de US$ 1.350k). SHAP mede o impacto por observação no conjunto de teste — como apenas 0.75% dos imóveis são waterfront, o SHAP médio é baixo mesmo com o impacto sendo imenso nos poucos casos positivos.

**Para decisões de negócio, SHAP é mais interpretável:** `lat`, `sqft_living` e `grade` são os três fatores que mais movem o preço para um imóvel qualquer. Para o usuário do assistente, isso se traduz em: localização, tamanho e qualidade construtiva determinam o valor do imóvel.

---

## 7. Limitações Técnicas

**Dados históricos (2014–2015):** as estimativas refletem o nível de preços daquele período. O mercado de Seattle valorizou significativamente desde então (~60–80% de valorização acumulada segundo índices públicos). Para uso atual, os valores precisariam ser ajustados por um índice de valorização ou o modelo precisaria ser retreinado com dados recentes.

**Extrapolação geográfica:** o modelo é válido apenas para zipcodes de King County. Coordenadas fora do range [47.15, 47.78] em latitude produzem previsões sem sentido — o modelo extrapola para fora do domínio treinado.

**Imóveis atípicos:** para waterfront, grade ≥ 11 e preços acima de US$ 2M, o modelo tem menos dados de treino e a margem de erro é maior. A quantile regression mitiga parcialmente esse problema ao gerar intervalos mais largos nesses casos — o P10–P90 se alarga automaticamente onde há menos dados.

**Multicolinearidade:** `sqft_living`, `sqft_above` e `sqft_living15` são altamente correlacionados. Em XGBoost isso não causa instabilidade de coeficientes, mas dificulta a interpretação isolada de cada feature. As importâncias devem ser lidas em conjunto, não individualmente.

**Sem dados macroeconômicos:** taxa de juros, inflação e oferta de mercado não estão no modelo. Mudanças abruptas de cenário econômico (como as ocorridas em 2022 com o aumento de juros nos EUA) não são capturadas e afetariam severamente a qualidade das previsões.

---

## 8. Caminhos Futuros

**Conformal prediction:** substituir ou complementar a quantile regression por conformal prediction para intervalos de confiança com cobertura garantida calibrada estatisticamente — o P10–P90 atual tem cobertura empírica (~80%), mas sem garantia formal.

**Embeddings geográficos:** representar `zipcode` com embeddings treinados ao invés de TargetEncoder pode melhorar a captura de similaridade entre bairros adjacentes que o encoding por mediana não captura.

**Ensemble com modelo geográfico:** adicionar um modelo de interpolação espacial (kriging ou vizinhos mais próximos) como feature de entrada pode capturar variações locais finas que o zipcode não resolve — por exemplo, diferenças de preço entre dois lados de uma avenida no mesmo zipcode.

**Reentreino com dados mais recentes:** a melhoria mais imediata em valor de negócio seria incorporar transações de 2020–2024 para refletir o mercado atual de Seattle. O pipeline de treino já está estruturado para isso — bastaria substituir o CSV de entrada e re-executar `app/ml/train.py`.

---

*Código de treinamento: [`app/ml/train.py`](../app/ml/train.py) | Artefatos: [`artifacts/model/metadata.json`](../artifacts/model/metadata.json)*
