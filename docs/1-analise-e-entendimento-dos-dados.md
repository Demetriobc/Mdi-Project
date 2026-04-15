# Entendimento dos Dados

---

## 1. Datasets Utilizados

### 1.1 `kc_house_data.csv` — Dataset principal

**Fonte:** King County Assessor (disponível publicamente via Kaggle)  
**Período:** Maio de 2014 a Maio de 2015  
**Volume:** 21.613 registros de vendas residenciais  
**Granularidade:** Uma linha por transação de venda  
**Cobertura geográfica:** King County, Washington (Seattle e municípios do entorno)

Este é o dataset central do projeto. Cada registro representa uma venda imobiliária e contém características físicas do imóvel, localização geográfica e data de transação. Após limpeza (remoção de duplicatas e outliers extremos), o dataset útil tem aproximadamente 21.420 registros.

---

### 1.2 `zipcode_demographics.csv` — Dados demográficos por zipcode

**Fonte:** Dados públicos por código postal  
**Granularidade:** Uma linha por zipcode  
**Volume:** 70 zipcodes únicos de King County

Este dataset enriquece o dataset principal com informações socioeconômicas do bairro, incluindo renda mediana das famílias, densidade populacional e percentual de proprietários. A integração é feita via `LEFT JOIN` usando `zipcode` como chave.

O papel direto das variáveis demográficas no modelo é indireto: elas não entram como features explícitas no pipeline de treino (o efeito já é capturado por `zipcode`, `lat` e `long`), mas enriquecem a knowledge base do RAG — o assistente conversacional usa essas informações ao responder perguntas sobre perfil socioeconômico dos bairros.

---

### 1.3 `future_unseen_examples.csv` — Exemplos para inferência

**Fonte:** Gerado para o projeto  
**Propósito:** Validar o pipeline de inferência em dados que nunca passaram pelo treinamento

Este arquivo contém imóveis hipotéticos ou de períodos não cobertos pelo treino. Serve para demonstrar que o modelo generaliza corretamente para novos dados e que o pipeline de pré-processamento + inferência funciona end-to-end sem o target disponível. Os resultados estão documentados em [`results/future_predictions.csv`](../results/future_predictions.csv).

---

## 2. O Que Representam as Variáveis Principais

O dataset KC House Sales cobre 21 variáveis originais. Entender o que cada uma captura no contexto do mercado imobiliário de King County é fundamental para interpretar o impacto delas no modelo.

### Variáveis de tamanho físico

| Variável | Tipo | O que representa na prática |
|---|---|---|
| `sqft_living` | Inteiro | Área útil interior em sqft — o principal indicador de capacidade habitacional. Inclui todos os andares mas exclui garagem. Correlação de 0.70 com o preço — a mais alta entre as variáveis contínuas. |
| `sqft_lot` | Inteiro | Área total do terreno. Em Seattle, terrenos maiores não implicam necessariamente preço maior: um lote grande em Auburn (periferia) vale menos que um menor em Capitol Hill (centro). |
| `sqft_above` | Inteiro | Área acima do nível do solo (exclui porão). Alta colinearidade com `sqft_living` (ρ = 0.88) — imóveis com porão têm `sqft_above < sqft_living`. |
| `sqft_basement` | Inteiro | Área do porão. Valor `0` indica ausência de porão (59% dos imóveis). Porões em King County são valorizados: mediana 15% superior para mesmo `sqft_above`. |
| `sqft_living15` | Inteiro | Média da área útil dos 15 vizinhos mais próximos — proxy da qualidade e porte do bairro. Correlação 0.59 com preço, superior ao número de quartos ou banheiros. |
| `sqft_lot15` | Inteiro | Média do tamanho de lote dos 15 vizinhos — contexto de densidade do entorno. |

### Variáveis de configuração do imóvel

| Variável | Tipo | O que representa na prática |
|---|---|---|
| `bedrooms` | Inteiro | Número de quartos. Correlação moderada com preço (0.31), pois um imóvel com mais quartos mas menor área por quarto pode valer menos que um com menos quartos e planta aberta de alta qualidade. |
| `bathrooms` | Float | Número de banheiros em escala fracionária (0.25 = lavabo, 0.5 = banheiro sem chuveiro, 0.75 = chuveiro sem banheira, 1.0 = completo). Correlação 0.53 — está associado ao padrão geral do imóvel. |
| `floors` | Float | Número de andares (1, 1.5, 2, 2.5, 3). A escala 0.5 indica mezanino ou sótão habitável. Impacto moderado no preço — relevante na interação com `sqft_living`. |

### Variáveis de qualidade e condição

| Variável | Tipo | O que representa na prática |
|---|---|---|
| `grade` | Ordinal (1–13) | Avaliação de qualidade de construção e design segundo a escala da King County Assessor. Vai de 1 (estrutura improvisada) a 13 (mansão de alto padrão arquitetônico). Valores 7–8 são a faixa residencial padrão em Seattle. Correlação 0.67 com preço, mas o efeito é fortemente não-linear — o salto de valor entre grades não é constante. |
| `condition` | Ordinal (1–5) | Estado de conservação: 1 = precisando de reforma urgente, 3 = condição média mantida, 5 = excelente conservação. Impacto menor que `grade` — o mercado pondera mais qualidade original de construção do que estado de conservação. |
| `view` | Ordinal (0–4) | Qualidade da vista: 0 = sem vista especial, 4 = vista panorâmica excepcional. Correlação 0.40; o efeito se concentra nos extremos (4 e, em menor grau, 3). |
| `waterfront` | Binário | Se o imóvel tem frente para a água (lago ou canal). Apenas 163 registros (0.75% do dataset), mas com premium de **+207%** na mediana — o maior efeito de qualquer variável binária do dataset. |

### Variáveis temporais

| Variável | Tipo | O que representa na prática |
|---|---|---|
| `yr_built` | Inteiro | Ano de construção (1900–2015). Usado para calcular `house_age`. Imóveis muito antigos (pré-1940) ou muito novos (pós-2010) têm comportamentos diferentes — os antigos podem ser valorizados por caráter histórico; os novos por acabamentos modernos. |
| `yr_renovated` | Inteiro | Ano da última reforma significativa. Valor `0` indica "nunca reformado" (não é missing). A diferença entre `yr_built` e `yr_renovated` indica se o imóvel foi modernizado. |
| `date` | String | Data da venda (YYYYMMDD). Usada para o split temporal e para extrair `sale_month`. Não entra como feature bruta no modelo. |

### Variáveis geográficas

| Variável | Tipo | O que representa na prática |
|---|---|---|
| `zipcode` | Categórico | 70 códigos postais de King County. Captura a variação entre bairros — a mediana varia de US$ 260k (98001, Auburn) a US$ 1.872.500 (98039, Medina). Tratado com **TargetEncoder** no preprocessamento. |
| `lat` / `long` | Float | Coordenadas geográficas. `lat` (47.15–47.78) captura o gradiente norte-sul: regiões ao norte de Seattle (Bellevue, Kirkland) são mais valorizadas. `long` (-122.52 a -121.31) captura o gradiente leste-oeste (Eastside vs. periferia sul). |

---

## 3. Estratégia de Integração dos Dados

O merge entre `kc_house_data.csv` e `zipcode_demographics.csv` é feito via `zipcode` como chave de junção:

```python
df = pd.merge(houses, demographics, on="zipcode", how="left")
```

**Por que LEFT JOIN:** garante que imóveis sem correspondência demográfica (caso raro de zipcode ausente no arquivo de demographics) não sejam descartados do treino. Para esses casos, os campos demográficos ficam nulos e são tratados no pré-processamento.

**O que o enriquecimento acrescenta:**

| Campo demográfico | Valor para o projeto |
|---|---|
| Renda mediana por zipcode | Contexto socioeconômico do bairro — útil no RAG para explicar ao usuário por que determinadas regiões são mais valorizadas |
| Densidade populacional | Diferencia bairros urbanos compactos de subúrbios — explica padrões de `sqft_lot` por região |
| % de proprietários | Proxy de estabilidade e perfil do bairro (locatários vs. proprietários) |

As variáveis demográficas foram avaliadas como features do modelo, mas não trouxeram ganho significativo em RMSE — a informação geográfica já está capturada por `zipcode`, `lat` e `long` com granularidade superior. A decisão foi mantê-las apenas na knowledge base do RAG.

---

## 4. Distribuição do Target (preço)

| Estatística | Valor |
|---|---|
| Mínimo | US$ 75.000 |
| Percentil 25 | US$ 321.950 |
| Mediana | US$ 450.000 |
| Média | US$ 540.088 |
| Percentil 75 | US$ 645.000 |
| Máximo | US$ 7.700.000 |
| Desvio padrão | US$ 367.127 |
| Skewness | ≈ 4.0 |

A distribuição é fortemente assimétrica à direita. A diferença entre mediana (US$ 450k) e média (US$ 540k) indica a influência de imóveis de luxo na cauda direita.

**Transformação aplicada:** `log1p(price)` no treino. A transformação logarítmica reduz a assimetria de ≈ 4.0 para ≈ 0.4, melhora a estabilidade do treino e reduz o peso desproporcional de outliers na função de perda. A previsão é reconvertida com `expm1` na inferência para devolver o valor em dólares.

**Por que isso importa:** sem a transformação, a função de perda (MSE/RMSE) seria dominada por imóveis de US$ 2M–7M. O modelo aprenderia a minimizar erros nos casos raros de luxo em detrimento dos imóveis típicos de US$ 300k–600k, que representam a maioria das transações e das consultas reais.

---

## 5. Correlações, Outliers e Padrões Relevantes

### 5.1 Correlações com o preço

Correlações de Pearson com `price` (antes da transformação log):

| Feature | Correlação | Observação |
|---|---|---|
| `sqft_living` | **0.70** | Variável quantitativa de maior correlação linear com o preço |
| `grade` | **0.67** | Ordinal — correlação linear subestima o impacto real (efeito não-linear nas faixas altas) |
| `sqft_above` | 0.61 | Alta colinearidade com `sqft_living` (ρ = 0.88) — captura o mesmo sinal |
| `sqft_living15` | 0.59 | Proxy de qualidade da vizinhança — bairros de casas grandes são mais caros |
| `bathrooms` | 0.53 | Correlacionado com tamanho e padrão construtivo |
| `view` | 0.40 | Ordinal — efeito não-linear concentrado nos valores 3 e 4 |
| `lat` | ~0.30 | Correlação linear baixa, mas impacto SHAP muito alto (1º lugar) — o gradiente geográfico não é linear |
| `waterfront` | 0.27 | Binária com impacto enorme nos casos positivos (+207% na mediana) |

**Importante:** correlações de Pearson capturam apenas relações lineares. `grade`, `zipcode`, `lat`/`long` e `waterfront` têm impacto real maior do que os coeficientes sugerem. Os valores SHAP do modelo final confirmam isso — `lat` assume a 1ª posição em impacto médio por observação, superando `sqft_living`.

**Multicolinearidade identificada:** `sqft_living`, `sqft_above` e `sqft_living15` são altamente correlacionados entre si (ρ > 0.75). Em XGBoost isso não causa instabilidade de coeficientes (diferente de regressão linear), mas dificulta a interpretação isolada de cada feature. As importâncias foram analisadas em conjunto via SHAP.

### 5.2 Outliers identificados e tratamento

| Caso | Volume | Tratamento | Justificativa |
|---|---|---|---|
| Imóvel com 33 quartos | 1 registro | **Removido** | Erro de digitação (o imóvel tem ~1.620 sqft — fisicamente impossível ter 33 quartos) |
| Preços abaixo de US$ 75.000 | < 5 registros | **Mantidos** | Possíveis vendas por distress, mas dentro do domínio válido do problema |
| `sqft_living` > 10.000 sqft | < 0.1% do dataset | **Mantidos** | Propriedades legítimas de luxo em Medina e Mercer Island — o modelo deve aprender esses casos |
| `grade` ≥ 11 com preço < US$ 500k | < 10 registros | **Mantidos** | Podem refletir imóveis mal avaliados ou em zipcodes de baixo valor; o modelo trata como dado válido |

O imóvel com 33 quartos é o único caso de remoção por erro claro de entrada. Os demais outliers de preço (imóveis > US$ 2M) são legítimos e pertencem a zipcodes específicos de alto valor — removê-los causaria viés na previsão para esse segmento.

### 5.3 Padrões relevantes descobertos na EDA

**Localização como fator dominante**  
A variação de preço entre zipcodes é maior do que qualquer característica física do imóvel. Um imóvel mediano em Medina (98039) vale 7x mais que um mediano em Auburn (98001). Isso explica por que `zipcode` e `lat`/`long` têm tanto peso preditivo — a localização é a variável mais importante mesmo antes do feature engineering.

**`grade` tem efeito exponencial, não linear**  
O salto de preço entre grades consecutivos acelera nas faixas altas:
- Grade 6 → 7: +27% na mediana
- Grade 7 → 8: +43% na mediana
- Grade 8 → 9: +40% na mediana
- Grade 9 → 10: +47% na mediana
- Grade 10 → 11: +68% na mediana

Esse comportamento exponencial é por isso que a correlação de Pearson (linear) subestima a importância de `grade` e por que XGBoost, que captura não-linearidades naturalmente, supera o Ridge nessa feature.

**Waterfront é o maior premium por variável binária**  
163 imóveis com frente para a água (0.75% do dataset) têm mediana de US$ 1.350.000 contra US$ 440.000 para os demais — um premium de **+207%**. Isso faz com que `waterfront` apareça com alto gain no XGBoost apesar da baixa frequência: cada split nessa feature é extremamente informativo.

**Sazonalidade moderada e consistente**  
Preços médios por mês de venda (base: média anual = 100%):
- Jan–Fev: ≈ -2% abaixo da média
- Mar–Abr: ≈ +1% acima
- Mai: ≈ +3.5% acima (pico de primavera)
- Jul–Ago: ≈ +2% acima
- Nov–Dez: ≈ -3% abaixo

O efeito é real mas pequeno em valor absoluto — US$ 15.000–20.000 para um imóvel típico. Foi capturado via feature `sale_month`.

**Vizinhança como amplificador de valor**  
`sqft_living15` (área média dos 15 vizinhos mais próximos) tem correlação 0.59 com o preço — maior do que `bedrooms` (0.31) ou `floors` (0.26). Estar num bairro de imóveis grandes é, por si só, um sinal de valor — independente do tamanho do imóvel avaliado. Isso motivou a feature derivada `living15_ratio` (área do imóvel / média dos vizinhos): imóveis acima do padrão local ganham prêmio adicional.

**Imóveis com porão têm prêmio consistente**  
41% dos imóveis têm porão. A mediana desses imóveis é 15% superior à de imóveis sem porão com o mesmo `sqft_above` — indicando que o mercado valora a área total mesmo quando parte é subterrânea. Esse padrão motivou a feature derivada `has_basement` (flag binária) além de usar `sqft_basement` diretamente.

**Reformas recentes valem mais do que reformas antigas**  
Imóveis reformados têm mediana 22% superior a não-reformados. Mas dentro dos reformados, a data da última reforma importa: reformas realizadas após 2005 apresentam prêmio médio de +30%, enquanto reformas pré-1990 têm prêmio de apenas +8%. Isso motivou a feature `years_since_renovation` que captura a "frescor" da reforma.

---

## 6. Features Derivadas (Feature Engineering)

Oito features foram criadas a partir das originais para capturar relações que modelos simples não capturariam diretamente:

| Feature | Fórmula | Racional |
|---|---|---|
| `house_age` | `2015 − yr_built` | Captura depreciação e potencial histórico — idade é um proxy de qualidade de construção e necessidade de atualização |
| `was_renovated` | `yr_renovated > 0` (flag binária) | Imóveis reformados têm mediana 22% superior; a flag separa os dois grupos |
| `years_since_renovation` | `2015 − yr_renovated` se reformado, senão `house_age` | Frescor da reforma — reformas recentes valem mais; usando `house_age` como fallback para não-reformados mantém a escala consistente |
| `living_lot_ratio` | `sqft_living / (sqft_lot + 1)` | Densidade de ocupação do terreno — proxy de perfil urbano (alta densidade = urbano) vs. suburbano |
| `bath_bed_ratio` | `bathrooms / (bedrooms + 1)` | Imóveis de padrão alto têm mais banheiros por quarto — razão alta é proxy de luxo |
| `has_basement` | `sqft_basement > 0` (flag binária) | Presença de porão (prêmio de 15% na mediana para mesmo `sqft_above`) |
| `living15_ratio` | `sqft_living / (sqft_living15 + 1)` | Relação do imóvel com o padrão da vizinhança — imóvel acima do padrão local ganha prêmio; abaixo sofre desconto |
| `sale_month` | Extraído de `date` | Sazonalidade — primavera tem preços ≈ 3.5% acima da média; inverno ≈ 2–3% abaixo |

O ano de referência para todos os cálculos temporais é **2015**, alinhado ao período máximo do dataset. O mesmo valor é usado em inferência (constante no código), o que é correto para o escopo histórico do modelo.

---

## 7. Qualidade dos Dados

### Missing values

O dataset KC House tem poucas ausências nos campos principais:

- `yr_renovated`: valor `0` significa "nunca reformado", não missing — tratado como dado válido com lógica específica em `feature_engineering.py`
- Campos demográficos (`zipcode_demographics.csv`): podem ter nulos para zipcodes sem correspondência — preenchidos com imputação pela mediana da região quando aplicável, ou descartados quando não há equivalente razoável
- Nenhuma feature do conjunto de treino tem taxa de missing > 1% após o merge

### Distribuição de zipcodes

70 zipcodes únicos cobrem desde Auburn (98001, mediana US$ 260k) até Medina (98039, mediana US$ 1.872.500). A variação entre os extremos é de **7x** — o que explica por que `zipcode` (via TargetEncoder) e `lat`/`long` têm tanto peso preditivo. O TargetEncoder substitui o código postal pela mediana do preço de venda naquele zipcode calculada exclusivamente no conjunto de treino, evitando vazamento de informação.

---

*Análise exploratória completa disponível em [`notebooks/01_eda.ipynb`](../notebooks/01_eda.ipynb).*
