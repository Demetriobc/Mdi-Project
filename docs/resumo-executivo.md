# Resumo Executivo — madeinweb

> Para líderes de negócio, produto e stakeholders não técnicos.

---

## Contexto do Problema

Estimar o preço justo de um imóvel é uma tarefa que depende de dezenas de variáveis interdependentes: localização, área, qualidade de construção, condição, vista, perfil do bairro. Avaliações manuais são demoradas, inconsistentes entre avaliadores e difíceis de escalar.

O desafio proposto foi construir uma solução de ponta a ponta capaz de prever o preço de imóveis em King County, Washington (área metropolitana de Seattle), com performance mensurável e uma interface utilizável por pessoas sem conhecimento técnico em dados.

---

## O Que Foi Construído

Uma aplicação completa com três camadas integradas:

**1. Modelo preditivo (núcleo da solução)**
Um modelo de machine learning treinado sobre 21.000+ transações imobiliárias reais. Dado um conjunto de características do imóvel, o modelo retorna uma estimativa de preço e um intervalo de confiança que indica a faixa provável de valor.

**2. Interface interativa**
Uma aplicação web com formulário de entrada, visualização do resultado com comparação à mediana do bairro, e resumo das principais características da estimativa.

**3. Assistente conversacional**
Um chat embutido na interface que responde perguntas em linguagem natural sobre o imóvel avaliado, os fatores que determinaram o preço e o comportamento do mercado local. O assistente usa o resultado do modelo como base — não realiza previsões por conta própria.

---

## Abordagem Adotada

O projeto seguiu três etapas principais:

**Dados:** Foram utilizados o dataset público King County House Sales (vendas de mai/2014 a mai/2015) e dados demográficos por código postal. Os dois foram integrados via zipcode para enriquecer o contexto geográfico de cada imóvel.

**Modelagem:** Foram testados dois modelos: uma regressão Ridge como baseline e XGBoost como modelo final. A avaliação foi feita com split temporal — o modelo foi treinado em dados anteriores a jan/2015 e testado em vendas posteriores, simulando previsão de valores futuros.

**Produto:** A solução foi empacotada em dois serviços independentes (API e frontend) com deploy automatizado via Docker e Railway. O modelo é treinado dentro da imagem Docker no momento do build, garantindo que o ambiente de produção seja reproduzível.

---

## Principais Resultados

O modelo XGBoost entregou melhora expressiva sobre o baseline em todas as métricas:

| Métrica | O que mede | Baseline | Modelo Final |
|---|---|---|---|
| **R²** | Capacidade explicativa do modelo | 0.76 | **0.89** |
| **MAE** | Erro médio absoluto em dólares | US$ 108.000 | **US$ 62.000** |
| **MAPE** | Erro percentual médio | 19,7% | **11,2%** |

**Em linguagem prática:** para um imóvel de US$ 500.000, o erro médio esperado é de aproximadamente US$ 56.000, ou seja, a estimativa tende a ficar entre US$ 444.000 e US$ 556.000. Para imóveis típicos de Seattle (grade 7–9, condition 3–4), a precisão é ainda melhor.

O sistema também gera um **intervalo de confiança P10–P90**: a faixa captura o preço real em ~80% dos casos no conjunto de teste.

**Variáveis que mais determinam o preço:**
1. Localização (latitude/zipcode)
2. Área útil interior (`sqft_living`)
3. Qualidade construtiva (`grade`)
4. Frente para a água (`waterfront`)
5. Vista (`view`)

---

## Como a Solução É Utilizada

O usuário acessa a aplicação pelo navegador, preenche os dados do imóvel (quartos, área, qualidade, localização) e clica em "Prever Preço". Em menos de um segundo, recebe:

- Estimativa central de preço
- Faixa provável (mínimo–máximo)
- Comparação com a mediana do bairro
- Opção de perguntar ao assistente sobre os fatores do resultado

Não é necessário nenhum conhecimento técnico para usar a interface.

---

## Limitações Conhecidas

É importante ser transparente sobre o escopo e os limites da solução:

**Dados históricos:** O modelo foi treinado com preços de 2014–2015. Os valores absolutos refletem o nível de preços daquele período. O mercado de Seattle valorizou significativamente desde então — as estimativas devem ser interpretadas como referência relativa, não como precificação atual.

**Escopo geográfico:** O modelo é válido apenas para imóveis em King County, WA. Aplicação em outros mercados produziria resultados sem significado.

**Segmentos atípicos:** Para imóveis de luxo (> US$ 1,5M), frente para a água ou com características muito fora do padrão, a margem de erro é maior.

**O que o modelo não captura:** Qualidade das escolas locais, proximidade a parques e transporte público, histórico de reformas internas, entre outros fatores qualitativos.

---

## Próximos Passos

Com a estrutura atual funcionando em produção, as evoluções mais relevantes seriam:

1. **Monitoramento de drift:** detectar automaticamente quando a distribuição dos dados de entrada muda e acionar alertas
2. **Reentreino periódico:** incorporar novos dados de vendas para manter a relevância do modelo ao mercado atual
3. **Ajuste de índice de valorização:** aplicar fator de correção de preços históricos para 2024 com base em índice imobiliário público
4. **Expansão geográfica:** adaptar o pipeline para outros mercados com datasets similares

---

*Documentação técnica detalhada disponível em [`docs/`](.).*
