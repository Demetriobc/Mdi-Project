# Limitações do Modelo — madeinweb-teste

Este documento descreve de forma honesta as limitações do modelo preditivo para
que usuários e analistas possam interpretar as previsões com o nível correto de confiança.

---

## 1. Escopo geográfico restrito

**Limitação**: O modelo foi treinado exclusivamente com dados de King County, Washington (EUA).

**Implicação**: Previsões para imóveis fora de King County são inválidas. Os padrões de preço, a escala de grade e os efeitos de localização são específicos deste mercado.

**Sinal de alerta**: Zipcodes fora do range 98001–98199 provavelmente produzirão previsões sem sentido.

---

## 2. Dados históricos (2014–2015)

**Limitação**: O dataset cobre vendas de maio de 2014 a maio de 2015. O mercado imobiliário de Seattle sofreu valorização significativa desde então (2016–2023 especialmente).

**Implicação**: Os valores absolutos previstos refletem o nível de preços de 2014–2015. Para uso em contexto atual, os valores devem ser ajustados por um índice de valorização (estimativa: +80–120% até 2024).

**O modelo é mais útil para**: Comparações relativas entre imóveis, análise de features determinantes de preço, e entendimento de padrões de mercado — não para precificação absoluta em tempo real.

---

## 3. Ausência de dados macroeconômicos

**Limitação**: O modelo não incorpora taxa de juros, inflação, índice de confiança do consumidor ou oferta/demanda de mercado.

**Implicação**: Mudanças abruptas de cenário econômico (como a alta de juros de 2022–2023) não são capturadas e podem tornar as previsões sistematicamente enviesadas.

---

## 4. Imóveis atípicos e outliers

**Limitação**: O modelo pode ter performance degradada em:
- Imóveis com características muito incomuns (grade > 11, bedrooms > 8, sqft_living > 7.000)
- Propriedades waterfront (apenas ~1% do dataset de treino)
- Imóveis de luxo acima de US$ 2M (cauda longa da distribuição)
- Imóveis com condição=1 (muito raros)

**Por quê**: Modelos de gradiente boosting têm dificuldade de extrapolar além do range de treino.

---

## 5. Ausência de informações qualitativas

**Limitação**: O modelo não captura:
- Qualidade das escolas do bairro
- Proximidade a parques, transporte público ou amenidades
- Ruído, tráfego ou fatores ambientais
- Histórico de crimes da área
- Qualidade interna (fotos, acabamento específico)

**Implicação**: Dois imóveis com mesmos atributos numéricos em bairros com perfis escolares diferentes podem ter preços de mercado distintos, e o modelo não captará essa diferença além do que o zipcode/lat/long conseguem aproximar.

---

## 6. Intervalos de confiança não disponíveis

**Limitação**: O modelo XGBoost padrão retorna um único valor pontual — sem intervalo de confiança ou estimativa de incerteza.

**Orientação de uso**:
- Para imóveis típicos (grade 6–9, condition 3–4, zipcode de alta frequência no treino): erro esperado de ±8–15%
- Para imóveis atípicos: erro esperado de ±20–40%
- A MAPE no conjunto de teste é o melhor indicador global de confiabilidade

**Trabalho futuro**: Implementar quantile regression ou conformal prediction para intervalos de confiança calibrados.

---

## 7. Vazamento temporal não controlado

**Limitação**: O split treino/teste é aleatório, não temporal. Em produção real, o ideal seria treinar em dados anteriores a uma data e testar em dados posteriores.

**Implicação**: A performance reportada pode ser ligeiramente otimista para um cenário de previsão de vendas futuras.

---

## 8. Multicolinearidade entre features

**Limitação**: `sqft_living`, `sqft_above`, `sqft_living15`, e `grade` são correlacionados entre si. Em modelos lineares isso seria crítico; em XGBoost, o impacto é menor, mas a importância individual de cada feature deve ser interpretada com cautela.

---

## Resumo da confiabilidade

| Cenário | Nível de confiança |
|---|---|
| Imóvel típico (grade 7–8, condition 3, Seattle/Eastside) | Alto |
| Imóvel médio fora do centro | Médio-alto |
| Imóvel muito caro (>$1.5M) ou muito barato (<$150k) | Médio |
| Imóvel waterfront ou grade 11–13 | Baixo-médio |
| Imóvel fora do King County | Inválido |
