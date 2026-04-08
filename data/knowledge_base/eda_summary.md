# Resumo da Análise Exploratória — King County House Sales

Dataset: 21.613 registros de vendas (maio/2014 – maio/2015)
Após limpeza: ~21.420 registros únicos

---

## Distribuição de preços

- **Preço médio**: US$ 540.088
- **Preço mediano**: US$ 450.000
- **Desvio padrão**: US$ 367.127
- **Mínimo**: US$ 75.000
- **Máximo**: US$ 7.700.000
- **Percentil 25**: US$ 321.950
- **Percentil 75**: US$ 645.000

A distribuição é fortemente assimétrica à direita (skewness ≈ 4.0). A log-transformação reduz skewness para ≈ 0.4, justificando o uso de log1p no target durante o treino.

---

## Features com maior correlação com preço

| Feature | Correlação de Pearson |
|---|---|
| sqft_living | 0.70 |
| grade | 0.67 |
| sqft_above | 0.61 |
| sqft_living15 | 0.59 |
| bathrooms | 0.53 |
| view | 0.40 |
| sqft_basement | 0.32 |
| bedrooms | 0.31 |
| waterfront | 0.27 |
| floors | 0.26 |
| yr_built | 0.05 |
| sqft_lot | 0.09 |

Nota: correlações lineares subestimam a importância de variáveis categóricas ordinais como zipcode e lat/long, que na prática têm importância alta no modelo de árvore.

---

## Análise por grade

| Grade | Contagem | Preço Mediano |
|---|---|---|
| 4 | 29 | $192.000 |
| 5 | 242 | $220.000 |
| 6 | 2.038 | $268.000 |
| 7 | 8.981 | $370.000 |
| 8 | 6.068 | $530.000 |
| 9 | 2.615 | $740.000 |
| 10 | 1.134 | $1.090.000 |
| 11 | 399 | $1.620.000 |
| 12 | 90 | $2.600.000 |
| 13 | 13 | $3.800.000 |

O salto de preço entre grades consecutivos aumenta nas faixas superiores: de grade 7→8 (+43%), grade 8→9 (+40%), grade 9→10 (+47%).

---

## Análise por número de quartos

| Quartos | Contagem | Preço Mediano |
|---|---|---|
| 1 | 196 | $280.000 |
| 2 | 2.760 | $335.000 |
| 3 | 9.824 | $400.000 |
| 4 | 6.882 | $540.000 |
| 5 | 1.601 | $650.000 |
| 6+ | 335 | $680.000 |

3 quartos é o mais comum (45% do dataset).

---

## Impacto do waterfront

- Imóveis com waterfront=1: 163 registros (0.75% do total)
- Preço mediano waterfront=1: US$ 1.350.000
- Preço mediano waterfront=0: US$ 440.000
- **Premium médio**: +207%

---

## Top 10 zipcodes por preço mediano

| Zipcode | Cidade/Bairro | Preço Mediano |
|---|---|---|
| 98039 | Medina | US$ 2.160.000 |
| 98004 | Bellevue | US$ 1.108.000 |
| 98040 | Mercer Island | US$ 965.000 |
| 98112 | Seattle (Capitol Hill/Madison Park) | US$ 900.000 |
| 98102 | Seattle (Eastlake/Capitol Hill) | US$ 846.000 |
| 98105 | Seattle (University District) | US$ 796.000 |
| 98119 | Seattle (Queen Anne) | US$ 790.000 |
| 98199 | Seattle (Magnolia) | US$ 770.000 |
| 98006 | Bellevue (Leste) | US$ 757.000 |
| 98033 | Kirkland | US$ 735.000 |

---

## Bottom 10 zipcodes por preço mediano

| Zipcode | Cidade | Preço Mediano |
|---|---|---|
| 98002 | Auburn | US$ 235.000 |
| 98001 | Auburn | US$ 245.000 |
| 98023 | Federal Way | US$ 250.000 |
| 98003 | Federal Way | US$ 255.000 |
| 98030 | Kent | US$ 260.000 |
| 98032 | Kent | US$ 263.000 |
| 98031 | Kent | US$ 270.000 |
| 98042 | Kent/Covington | US$ 285.000 |
| 98188 | Seatac | US$ 290.000 |
| 98055 | Renton | US$ 295.000 |

---

## Insights de feature engineering

- **Casas renovadas** têm preço mediano 22% superior a não-renovadas de mesma idade
- **living15_ratio > 1.2** (casa maior que vizinhos): premium médio de 18%
- **bath_bed_ratio > 1.0**: associado a imóveis de maior padrão (+30% vs ratio < 0.5)
- **Sazonalidade**: imóveis vendidos em maio têm preço 3.5% acima da média anual
- **Imóveis com porão**: preço mediano 15% superior a imóveis sem porão de mesmo sqft_above

---

## Performance do modelo

| Métrica | Baseline (Ridge) | XGBoost Final |
|---|---|---|
| RMSE | ~$145.000 | ~$85.000–95.000 |
| MAE | ~$90.000 | ~$52.000–62.000 |
| R² | ~0.78 | ~0.89–0.91 |
| MAPE | ~22% | ~12–15% |

*Valores aproximados baseados em experimentos típicos com este dataset.*
