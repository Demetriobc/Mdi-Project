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

**Variáveis originais do dataset:**

| Variável | Tipo | Descrição |
|---|---|---|
| `id` | Identificador | ID da transação (não entra no modelo) |
| `date` | String | Data da venda no formato YYYYMMDD |
| `price` | Float | Preço de venda em dólares (target) |
| `bedrooms` | Inteiro | Número de quartos |
| `bathrooms` | Float | Número de banheiros (escala 0.25–0.5–0.75–1.0) |
| `sqft_living` | Inteiro | Área útil interior em sqft |
| `sqft_lot` | Inteiro | Área total do lote em sqft |
| `floors` | Float | Número de andares |
| `waterfront` | Binário | Frente para a água (0/1) |
| `view` | Ordinal (0–4) | Qualidade da vista |
| `condition` | Ordinal (1–5) | Condição do imóvel |
| `grade` | Ordinal (1–13) | Qualidade de construção e design (escala King County) |
| `sqft_above` | Inteiro | Área acima do nível do solo |
| `sqft_basement` | Inteiro | Área do porão (0 = sem porão) |
| `yr_built` | Inteiro | Ano de construção |
| `yr_renovated` | Inteiro | Ano da última renovação (0 = nunca reformado) |
| `zipcode` | Categórico | Código postal (70 valores únicos em King County) |
| `lat` / `long` | Float | Coordenadas geográficas |
| `sqft_living15` | Inteiro | Área útil média dos 15 vizinhos mais próximos |
| `sqft_lot15` | Inteiro | Área de lote média dos 15 vizinhos mais próximos |

---

### 1.2 `zipcode_demographics.csv` — Dados demográficos por zipcode

**Fonte:** Dados públicos por código postal  
**Granularidade:** Uma linha por zipcode  
**Volume:** 70 zipcodes únicos de King County

Este dataset enriquece o dataset principal com informações socioeconômicas do bairro, incluindo renda mediana das famílias, densidade populacional e percentual de proprietários. A integração é feita via `LEFT JOIN` usando `zipcode` como chave.

O impacto direto no modelo é indireto: as variáveis demográficas não entram explicitamente nas features finais, mas enriquecem o contexto disponível para a knowledge base do RAG e podem ser incorporadas em versões futuras do modelo.

---

### 1.3 `future_unseen_examples.csv` — Exemplos para inferência

**Fonte:** Gerado para o projeto  
**Propósito:** Validar o pipeline de inferência em dados que nunca passaram pelo treinamento

Este arquivo contém imóveis hipotéticos ou de períodos não cobertos pelo treino. Serve para demonstrar que o modelo generaliza corretamente para novos dados e que o pipeline de pré-processamento + inferência funciona end-to-end sem o target disponível. Os resultados estão documentados em [`results/future_predictions.csv`](../results/future_predictions.csv).

---

## 2. Estratégia de Integração

O merge entre `kc_house_data.csv` e `zipcode_demographics.csv` é feito via `zipcode` como chave de junção:

```python
df = pd.merge(houses, demographics, on="zipcode", how="left")
```

A escolha de `LEFT JOIN` garante que imóveis sem correspondência demográfica (caso o zipcode não esteja no arquivo de demographics) não sejam descartados. Para esses casos, os campos demográficos ficam nulos e são tratados no pré-processamento.

---

## 3. Distribuição do Target (preço)

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

A distribuição é fortemente assimétrica à direita. A diferença entre mediana (US$ 450k) e média (US$ 540k) indica a influência de imóveis de luxo na cauda da distribuição.

**Transformação aplicada:** `log1p(price)` no treino. A transformação logarítmica reduz a assimetria de ≈ 4.0 para ≈ 0.4, melhora a estabilidade do treino e reduz o peso desproporcional de outliers na função de perda. A previsão é reconvertida com `expm1` na inferência.

---

## 4. Features com Maior Correlação com o Preço

Correlações de Pearson com `price` (antes da transformação log):

| Feature | Correlação | Observação |
|---|---|---|
| `sqft_living` | 0.70 | Variável quantitativa de maior correlação linear |
| `grade` | 0.67 | Ordinal — correlação linear subestima o impacto real |
| `sqft_above` | 0.61 | Alta colinearidade com `sqft_living` |
| `sqft_living15` | 0.59 | Proxy de qualidade da vizinhança |
| `bathrooms` | 0.53 | Correlacionado com tamanho e padrão |
| `view` | 0.40 | Ordinal — efeito não-linear nas faixas altas |
| `waterfront` | 0.27 | Binária com impacto muito alto nos casos positivos (+207% na mediana) |
| `lat` | ~0.30 | Coordenadas geográficas têm correlação linear baixa mas impacto SHAP alto |

**Nota importante:** correlações de Pearson capturam apenas relações lineares. Variáveis categóricas ordinais como `grade` e `zipcode`, e variáveis geográficas como `lat`/`long`, têm impacto real maior do que os coeficientes de correlação sugerem. Isso é confirmado pelos valores SHAP do modelo final, onde `lat` assume a primeira posição.

---

## 5. Features Derivadas (Feature Engineering)

Oito features foram criadas a partir das originais para capturar relações que o modelo linear não capturaria diretamente:

| Feature | Fórmula | Racional |
|---|---|---|
| `house_age` | `2015 - yr_built` | Captura depreciação e potencial histórico |
| `was_renovated` | `yr_renovated > 0` (flag) | Imóveis reformados têm mediana 22% superior |
| `years_since_renovation` | `2015 - yr_renovated` (se renovado) ou `house_age` | Frescor da reforma — renovações recentes valem mais |
| `living_lot_ratio` | `sqft_living / sqft_lot` | Densidade de ocupação — proxy de perfil urbano |
| `bath_bed_ratio` | `bathrooms / (bedrooms + 1)` | Imóveis de luxo têm ratio alto |
| `has_basement` | `sqft_basement > 0` (flag) | Presença de porão (+15% na mediana para mesmo sqft_above) |
| `living15_ratio` | `sqft_living / sqft_living15` | Relação com vizinhos — imóvel acima do padrão local tem prêmio |
| `sale_month` | Extraído de `date` | Sazonalidade — primavera tem preços ≈ 3.5% acima da média anual |

O ano de referência para todos os cálculos temporais é **2015**, alinhado ao período do dataset.

---

## 6. Qualidade dos Dados

### Missing values

O dataset KC House tem poucas ausências nos campos principais. Os casos identificados:

- `yr_renovated`: valor `0` significa "nunca reformado", não missing — tratado como dado válido
- Campos demográficos: podem ter nulos para zipcodes sem correspondência no arquivo de demographics — tratados com imputação ou descartados conforme a feature

### Outliers identificados

| Caso | Volume | Tratamento |
|---|---|---|
| Imóvel com 33 quartos | 1 registro | Removido — erro de digitação |
| Preços abaixo de US$ 75.000 | Poucos casos | Mantidos — podem ser vendas por distress, mas são raros |
| Imóveis com `sqft_living` > 10.000 | < 0.1% | Mantidos — propriedades legítimas de luxo |

### Distribuição de zipcodes

70 zipcodes únicos cobrem desde Auburn (98001, mediana US$ 260k) até Medina (98039, mediana US$ 1.872.500). A variação entre zipcodes extremos é de **7x** — o que explica por que `zipcode` e `lat`/`long` têm tanto peso preditivo.

---

## 7. Insights Principais da Análise Exploratória

**Localização como fator dominante**  
A variação de preço entre zipcodes é maior do que a variação explicada por qualquer característica física do imóvel. Um imóvel mediano em Medina (98039) vale 7x mais do que um mediano em Auburn (98001). Latitude e zipcode capturam essa variação diretamente no modelo.

**Grade como proxy de padrão construtivo**  
O salto de preço entre grades consecutivos não é linear — se acelera nas faixas superiores:
- Grade 7 → 8: +43% na mediana
- Grade 8 → 9: +40%
- Grade 9 → 10: +47%

**Waterfront é o maior premium por variável binária**  
163 imóveis com frente para a água (0,75% do dataset) têm mediana de US$ 1.350.000 contra US$ 440.000 para os demais — um premium de **+207%**. Isso torna `waterfront` muito influente no ganho do XGBoost apesar da baixa frequência.

**Sazonalidade existe mas é moderada**  
Imóveis vendidos em maio têm preço ≈ 3,5% acima da média anual. O efeito é real mas pequeno em termos absolutos — US$ 15.000–20.000 para um imóvel típico.

**Vizinhança como amplificador de valor**  
`sqft_living15` (área média dos 15 vizinhos mais próximos) tem correlação de 0.59 com o preço — maior do que o número de quartos ou banheiros. Estar num bairro de imóveis grandes é, por si só, um sinal de valor.

**Imóveis com porão têm prêmio**  
41% dos imóveis têm porão. A mediana desses imóveis é 15% superior à de imóveis sem porão com o mesmo `sqft_above` — indicando que o mercado valoriza a área total mesmo quando parte dela é subterrânea.

---

*Análise exploratória completa disponível em `notebooks/01_eda.ipynb`.*
