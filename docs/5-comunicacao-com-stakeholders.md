# Comunicação com Stakeholders

---

## 1. Públicos e Abordagens

Resultados de modelos preditivos precisam ser comunicados de formas diferentes dependendo do público. Uma explicação técnica precisa para um engenheiro é ruído para um diretor de negócio. O contrário também é verdade.

| Público | O que importa | O que evitar |
|---|---|---|
| **Liderança executiva** | Valor gerado, precisão em linguagem simples, limitações honestas | Hiperparâmetros, fórmulas, detalhes técnicos |
| **Equipe de produto** | Como a solução funciona, o que o usuário vê, limitações de UX | Matemática interna, detalhes de infraestrutura |
| **Equipe técnica** | Decisões de arquitetura, métricas completas, código | Simplificações excessivas |
| **Usuário final** | O que fazer com o resultado, quanto confiar, como usar o chat | Como o modelo foi treinado |

---

## 2. Traduzindo Métricas para Linguagem de Negócio

As métricas estatísticas fazem sentido para quem as conhece, mas são ininteligíveis para a maioria dos tomadores de decisão. A tradução é obrigatória.

### R² = 0.891

**Versão técnica:** o modelo explica 89,1% da variância do preço de venda.

**Versão para negócio:**
> "O modelo consegue capturar 89% dos fatores que determinam o preço. Para comparação, uma estimativa pela mediana do bairro explicaria cerca de 76% — o modelo vai 13 pontos percentuais além do que uma análise simples já consegue."

### MAE = US$ 62.000

**Versão técnica:** o erro absoluto médio é de US$ 62.083.

**Versão para negócio:**
> "Para um imóvel de US$ 500.000, a estimativa tende a errar, em média, cerca de US$ 62.000 para cima ou para baixo. Isso equivale a uma margem de ±12%. Para decisões de avaliação e comparação de mercado, essa precisão é funcional."

### MAPE = 11,2%

**Versão técnica:** o erro percentual absoluto médio é de 11,24%.

**Versão para negócio:**
> "Em média, a estimativa fica a 11% do preço real. Imóveis típicos de Seattle (padrão médio, localização central) têm erros menores — na faixa de 8–9%. Imóveis de luxo ou muito atípicos podem ter erros maiores."

### Intervalo P10–P90

**Versão técnica:** o intervalo de quantis 10 e 90 captura o preço real em ~80% dos casos no conjunto de teste.

**Versão para negócio:**
> "Além do preço central, o sistema mostra uma faixa de valores. Para o imóvel avaliado, essa faixa tem 80% de chance de conter o preço real de mercado. Quanto mais estreita a faixa, mais confiante o modelo está."

---

## 3. Visualizações Recomendadas para Apresentação

### 3.1 Comparação baseline vs modelo final

**Tipo:** gráfico de barras agrupadas, uma barra por métrica (MAE, RMSE), comparando Ridge e XGBoost.

**Por que funciona:** mostra a melhoria sem precisar de número absoluto. A barra menor do XGBoost comunica visualmente o avanço.

**O que incluir:** percentual de melhoria em anotação acima de cada par de barras.

### 3.2 Importância de features (SHAP)

**Tipo:** gráfico de barras horizontais ordenado por valor SHAP médio, com nome legível de cada feature.

**Por que funciona:** mostra quais fatores o modelo aprendeu a usar — vai ao encontro da intuição do mercado (localização, tamanho, qualidade).

**Como explicar para não técnicos:**
> "Essas barras mostram o quanto cada característica do imóvel contribui, em média, para mover o preço estimado. Localização responde por quase 30% da determinação de preço — mais do que a área ou qualidade de construção isoladamente."

### 3.3 Previsão vs valor real (scatter plot)

**Tipo:** scatter plot com eixo X = preço real, eixo Y = preço previsto. Linha diagonal ideal em vermelho pontilhado.

**Por que funciona:** pontos próximos da diagonal mostram que o modelo acerta; pontos distantes revelam onde ele erra sistematicamente (geralmente imóveis muito caros, onde os pontos tendem a ficar abaixo da diagonal — o modelo subestima os extremos).

**Como explicar:**
> "Cada ponto é um imóvel do conjunto de teste. Pontos na diagonal significam previsão perfeita. Quanto mais dispersos, maior o erro. Veja que para a maioria dos imóveis os pontos estão próximos — os casos mais distantes são imóveis de alto valor, onde qualquer modelo tem mais incerteza."

### 3.4 Distribuição do erro

**Tipo:** histograma do erro percentual (previsão - real) / real.

**Por que funciona:** mostra que os erros são aproximadamente centrados em zero (sem viés sistemático) e que a maioria fica entre -15% e +15%.

### 3.5 Intervalo de confiança para casos específicos

**Tipo:** gráfico de ponto com barra de erro (dot plot), mostrando previsão central + intervalo P10–P90 para 5–10 imóveis de referência.

**Por que funciona:** concretiza o conceito de incerteza de forma visual. É fácil mostrar que imóveis típicos têm intervalos estreitos e imóveis atípicos têm intervalos largos.

---

## 4. Como Apresentar Limitações Sem Descredibilizar

Apresentar limitações é obrigatório para ganhar credibilidade — e pode ser feito de forma que fortalece, não enfraquece, a apresentação.

**Princípio:** apresente a limitação junto com o contexto de quando ela importa e quando não importa.

**Exemplo — dados históricos:**

❌ Versão fraca:
> "O modelo só tem dados de 2014–2015, então os preços estão desatualizados."

✅ Versão forte:
> "O dataset cobre 2014–2015. Os valores absolutos refletem o nível de preços daquele período. O que o modelo entrega com alta confiança são as relações relativas entre características — quanto vale ter frente para a água, quanto cada nível de grade agrega, como a localização afeta o preço. Para usar os valores absolutos em 2024, aplicar um fator de correção baseado em índice imobiliário (estimativa: +80–100% de valorização) é suficiente."

**Exemplo — imóveis de luxo:**

❌ Versão fraca:
> "O modelo não funciona bem para imóveis caros."

✅ Versão forte:
> "Para o segmento acima de US$ 1,5M — menos de 3% do mercado de King County — o modelo tem menos dados de treino e a incerteza é maior. Nesses casos, o intervalo P10–P90 é mais largo, o que o sistema comunica explicitamente. Para o segmento médio, onde a maioria das decisões ocorre, a precisão é alta."

---

## 5. Storytelling com os Resultados

Uma boa apresentação dos resultados segue uma narrativa, não uma lista de métricas:

**Estrutura sugerida para apresentação de 10 minutos:**

```
1. O problema (1 min)
   "Estimar o preço de um imóvel manualmente depende de experiência, 
   tempo e acesso a dados de mercado. Erros de avaliação custam caro 
   para compradores, vendedores e corretoras."

2. A solução (2 min)
   Demo ao vivo ou screenshots. Mostrar o fluxo completo: 
   formulário → resultado → chat. Deixar o produto falar.

3. Como foi construído (2 min)
   Dados (21k transações reais), modelo (XGBoost), deploy (Railway).
   Sem entrar em detalhes técnicos — foco na consistência da abordagem.

4. Resultados (3 min)
   Baseline vs modelo final. Uma métrica central (MAE em dólares).
   Intervalo de confiança. O que as variáveis mais importantes dizem 
   sobre o mercado.

5. Limitações e próximos passos (2 min)
   Ser honesto sobre os dados históricos. Mostrar que o sistema já 
   comunica incerteza ao usuário. Detalhar o caminho para evolução.
```

---

## 6. Posicionando a Camada Conversacional para Usuários Finais

O chat é uma feature de alto impacto de UX, mas pode gerar confusão se não for bem comunicado. A mensagem precisa ser clara:

**O que comunicar:**
- O chat responde perguntas sobre o imóvel que você acabou de avaliar
- Ele explica por que o modelo chegou naquele preço
- Ele tem contexto sobre o mercado de King County
- As respostas podem ter imprecisões — validar com fontes especializadas para decisões importantes

**Como comunicar na interface:**

A aplicação já inclui o aviso: *"As respostas podem conter imprecisões. Sempre valide informações importantes."* Esse aviso está correto e deve ser mantido.

**Como posicionar numa apresentação:**
> "O chat não substitui um corretor de imóveis ou avaliador profissional. Ele funciona como um assistente que ajuda a entender os fatores por trás do preço estimado — em linguagem natural, sem precisar interpretar gráficos ou tabelas. Para um usuário que não sabe o que é 'grade 8', o chat explica o que isso significa e quanto impacta o valor."

**O que evitar comunicar:**
- Que o chat "sabe" o preço do imóvel (o preço vem do modelo XGBoost)
- Que o chat tem acesso a dados de mercado em tempo real (não tem)
- Que o chat substitui avaliação profissional

---

## 7. Demonstrando Valor

Para um avaliador técnico ou de negócio, os pontos de valor mais defensáveis do projeto são:

**1. Solução end-to-end funcionando em produção**  
Não é um notebook — é uma aplicação com API, interface e deploy. Isso demonstra capacidade de execução além da modelagem.

**2. Decisões técnicas defensáveis**  
Split temporal (não aleatório), early stopping, quantile regression para intervalo de confiança, transformação log1p do target — cada decisão tem justificativa técnica e pode ser explicada numa entrevista.

**3. Melhoria significativa sobre o baseline**  
−43% de MAE e +17pp de R² sobre Ridge não é trivial. Vem de bom feature engineering e configuração cuidadosa do modelo, não de força bruta.

**4. Transparência sobre limitações**  
Dados históricos, escopo geográfico, imóveis atípicos — tudo documentado e comunicado na interface. Isso é maturidade, não fraqueza.

**5. Arquitetura escalável**  
Dois serviços independentes, Docker, variáveis de ambiente, health checks — a estrutura está pronta para evoluir para produção real com volume real.
