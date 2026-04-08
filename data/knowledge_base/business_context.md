# Contexto de Negócio — Mercado Imobiliário de King County

## Sobre King County

King County é o condado mais populoso do estado de Washington (EUA), abrigando Seattle e mais de 40 municípios. O mercado imobiliário local é caracterizado por forte demanda impulsionada pela presença de grandes empregadores de tecnologia (Amazon, Microsoft, Boeing), alta qualidade de vida e oferta limitada de imóveis próximos ao centro.

O dataset utilizado neste sistema cobre vendas realizadas entre maio de 2014 e maio de 2015, período de aquecimento do mercado pós-crise de 2008 e início do boom tecnológico de Seattle.

## Fatores que determinam o preço

### 1. Localização
A localização é o fator mais determinante no preço de imóveis em King County. Zipcodes próximos ao lago Washington (Bellevue, Mercer Island, Kirkland) e ao centro de Seattle consistentemente apresentam preços 40–120% acima da mediana do condado. A latitude e longitude capturam esse efeito geográfico diretamente no modelo.

### 2. Área útil (sqft_living)
A área útil interior é a variável quantitativa com maior correlação com o preço. Cada 100 sqft adicionais impactam o preço em aproximadamente US$ 15.000–25.000 dependendo do zipcode. Imóveis acima de 3.000 sqft pertencem ao segmento premium.

### 3. Qualidade de construção (grade)
O sistema de classificação da King County Assessment Office vai de 1 a 13:
- Grades 1–3: Abaixo do código mínimo de construção
- Grades 4–6: Construção de baixo custo ou antiga
- Grade 7: Construção padrão (média do mercado)
- Grades 8–10: Acabamento superior, melhor qualidade de materiais
- Grades 11–13: Luxo, design customizado, materiais premium

A diferença de preço entre grade 7 e grade 10 é tipicamente de 30–60%.

### 4. Condição do imóvel (condition)
Escala de 1 a 5 avaliada pela inspeção do condado:
- 1: Ruim — requer reforma extensiva imediata
- 2: Razoável — apresenta desgaste significativo
- 3: Bom — manutenção adequada, estado médio (mais comum)
- 4: Muito bom — bem mantido, poucas necessidades
- 5: Excelente — estado impecável, pode incluir upgrades

### 5. Vista e frente para a água
Imóveis com vista para a água (waterfront=1) são os mais valorizados do condado, com premium médio de 150–300% sobre imóveis similares sem vista. A variável `view` (0–4) captura qualidade da vista em geral, com cada incremento adicionando aproximadamente 8–15% ao valor.

## Segmentos de mercado em King County

| Faixa de preço | Segmento | Características típicas |
|---|---|---|
| < $300.000 | Entrada | 2–3 quartos, subúrbios sul (Auburn, Federal Way, Kent) |
| $300k–$500k | Médio | 3 quartos, Renton, Kirkland norte, Seattle periférico |
| $500k–$800k | Médio-alto | 3–4 quartos, Bellevue leste, Kirkland, Seattle central |
| $800k–$1.5M | Alto | 4+ quartos, Bellevue, Mercer Island, Queen Anne |
| > $1.5M | Luxo | Imóveis premium, frente para a água, Medina, Cap Hill |

## Sazonalidade

O mercado KC apresenta padrão sazonal claro: primavera (março–junho) concentra o maior volume de transações e preços ligeiramente superiores. Inverno (novembro–fevereiro) tem menor liquidez. O modelo captura sazonalidade via `sale_month`.

## Tendências do período 2014–2015

- Valorização anual média do condado: ~10–12%
- Zipcodes de Seattle central valorizaram acima de 15% no período
- Estoque de imóveis disponíveis estava em mínima histórica
- Tempo médio de venda: 15–30 dias nos zipcodes premium
