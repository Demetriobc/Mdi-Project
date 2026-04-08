# Dicionário de Features — King County House Sales

Este documento descreve em linguagem natural cada variável do dataset e como ela
influencia o preço previsto pelo modelo.

---

## Features originais do dataset

### bedrooms — Número de quartos
- **Tipo**: Inteiro
- **Range típico**: 1–6 (outliers chegam a 10+)
- **Impacto no preço**: Positivo, mas não-linear. Após 5 quartos, o incremento marginal diminui. Um imóvel com 33 quartos foi detectado como erro de digitação e removido na limpeza.
- **Nota**: Imóveis com 0 quartos existem (estúdios) e são raros no dataset.

### bathrooms — Número de banheiros
- **Tipo**: Float (incrementos de 0.25 ou 0.5)
- **Range típico**: 0.5–4.5
- **Escala King County**: 0.25 = banheiro sem pia; 0.5 = banheiro sem chuveiro; 0.75 = banheiro completo sem banheira; 1.0 = banheiro completo
- **Impacto**: Alto. Cada banheiro adicional agrega ~US$ 20.000–40.000 dependendo da grade.

### sqft_living — Área útil interior (sqft)
- **Tipo**: Inteiro
- **Range típico**: 370–6.000 sqft
- **Impacto**: Muito alto. É a feature com maior poder preditivo quantitativo.
- **Referência**: 1 sqft ≈ 0.093 m²; uma casa de 1.800 sqft ≈ 167 m²

### sqft_lot — Área total do lote (sqft)
- **Tipo**: Inteiro
- **Range**: 520 a 1.651.359 sqft
- **Impacto**: Moderado. Terrenos grandes adicionam valor, especialmente em áreas rurais. Em zipcodes urbanos, o impacto é menor pois a área construível é mais relevante.

### floors — Número de andares
- **Tipo**: Float (1.0, 1.5, 2.0, 2.5, 3.0, 3.5)
- **Impacto**: Moderado-positivo. Casas de 2 andares tendem a ser maiores e mais valorizadas. 1.5 andares indica um meio-andar ou sótão parcialmente acabado.

### waterfront — Frente para a água
- **Tipo**: Binário (0 = não, 1 = sim)
- **Frequência**: ~1% do dataset
- **Impacto**: Muito alto. Premium médio de 150–300% sobre imóveis comparáveis sem vista para a água.

### view — Qualidade da vista
- **Tipo**: Ordinal (0–4)
- **Escala**: 0 = nenhuma vista; 1 = vista razoável; 2 = vista média; 3 = boa vista; 4 = vista excelente
- **Impacto**: Positivo. Cada nível adiciona aproximadamente 8–15% ao valor.

### condition — Condição do imóvel
- **Tipo**: Ordinal (1–5)
- **Escala**: 1 = ruim, 2 = razoável, 3 = bom (média), 4 = muito bom, 5 = excelente
- **Distribuição**: ~65% dos imóveis têm condition=3
- **Impacto**: Moderado. A diferença entre condition 3 e 5 é tipicamente 10–20%.

### grade — Qualidade de construção e design
- **Tipo**: Ordinal (1–13)
- **Escala King County**:
  - 1–3: Abaixo do código mínimo
  - 4–6: Construção de baixo custo
  - 7: Construção padrão (mediana)
  - 8–10: Acabamento superior
  - 11–13: Design customizado, luxo
- **Distribuição**: 77% dos imóveis têm grade entre 6 e 9
- **Impacto**: Muito alto. Uma das features mais importantes do modelo.

### sqft_above — Área acima do nível do solo (sqft)
- **Tipo**: Inteiro
- **Relação**: sqft_above + sqft_basement = sqft_living
- **Impacto**: Similar ao sqft_living, com ligeira preferência do mercado por área acima do solo.

### sqft_basement — Área do porão (sqft)
- **Tipo**: Inteiro (0 = sem porão)
- **Frequência de porão**: ~41% dos imóveis têm porão
- **Impacto**: Positivo, mas porão é valorizado menos por sqft do que área acima do solo (~60–70% do valor por sqft).

### yr_built — Ano de construção
- **Tipo**: Inteiro (1900–2015)
- **Impacto**: Não-linear. Casas muito antigas (<1940) ou muito novas (>2000) tendem a ser mais valorizadas. Casas de 1960–1980 tendem a ter preços mais baixos comparativamente.

### yr_renovated — Ano de última renovação
- **Tipo**: Inteiro (0 = nunca reformado)
- **Frequência de renovação**: ~4% dos imóveis foram reformados
- **Impacto**: Positivo quando recente. Reformas após 2000 têm impacto mais expressivo.

### zipcode — Código postal
- **Tipo**: Categórico (string de 5 dígitos)
- **Unique values**: 70 zipcodes únicos em King County
- **Impacto**: Muito alto. É um proxy poderoso de localização, vizinhança, escola e infraestrutura.

### lat / long — Coordenadas geográficas
- **Tipo**: Float
- **Range**: lat ∈ [47.15, 47.78], long ∈ [-122.52, -121.31]
- **Impacto**: Muito alto. Capturam micro-localização dentro do zipcode. lat é particularmente importante — zipcodes mais ao norte de Seattle têm correlação positiva com preço.

### sqft_living15 — Área útil média dos 15 vizinhos mais próximos
- **Tipo**: Inteiro
- **Impacto**: Alto. Bom proxy da qualidade e padrão da vizinhança. Imóveis em regiões com vizinhos de alto padrão tendem a ter maior valorização.

### sqft_lot15 — Área de lote média dos 15 vizinhos
- **Tipo**: Inteiro
- **Impacto**: Moderado. Indica densidade urbana do entorno.

---

## Features engenheiradas pelo modelo

### house_age
Calculado como 2015 - yr_built. Captura o efeito de depreciação e valor histórico.

### was_renovated
Flag binária. Indica se o imóvel passou por reforma (yr_renovated > 0).

### years_since_renovation
Se reformado: anos desde a renovação. Se não: igual a house_age. Captura frescor da reforma.

### living_lot_ratio
sqft_living / sqft_lot. Mede a densidade de ocupação do lote. Valores altos indicam imóveis urbanos densamente construídos.

### bath_bed_ratio
bathrooms / (bedrooms + 1). Ratio que captura o equilíbrio entre banheiros e quartos — imóveis de luxo tendem a ter ratio alto.

### has_basement
Flag binária (sqft_basement > 0). Simplificação do porão para capturar presença/ausência.

### living15_ratio
sqft_living / sqft_living15. Mede se o imóvel é maior ou menor que seus vizinhos. Valores > 1 indicam imóvel acima da média da região.

### sale_month
Mês da venda extraído de `date`. Captura sazonalidade (primavera tende a ter preços ligeiramente mais altos).
