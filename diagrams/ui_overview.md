# Diagrama: Visão Geral da Interface

## Objetivo

Mostrar o fluxo do usuário na aplicação — desde a entrada dos dados até a interpretação do resultado — e como os três painéis da interface (formulário, resultado, chat) se relacionam. O diagrama deixa claro em qual momento cada camada da solução é acionada.

## Blocos

| Bloco | Papel |
|---|---|
| **Sidebar (formulário)** | Painel esquerdo com controles de entrada: quartos, banheiros, área, andares, grade, condição, waterfront, vista, zipcode |
| **Botão "Prever Preço"** | Aciona o POST /predict — único ponto de entrada para o modelo ML |
| **MainContent (resultado)** | Painel central com estimativa, intervalo P10–P90, comparação com mediana do bairro, cards de features, localização |
| **ChatPanel (assistente)** | Painel direito com chat conversacional; acionado pelo usuário para explicações |
| **POST /predict** | API retorna preço central, p10, p90, mediana do zipcode |
| **POST /chat** | API usa RAG + LLM para responder perguntas contextualizadas |

---

## Diagrama Mermaid — Fluxo do Usuário

```mermaid
flowchart TD
    Start(["👤 Usuário acessa\na aplicação"])

    subgraph UI["Interface React (3 painéis)"]
        subgraph Sidebar["⬅️ Sidebar — Formulário"]
            Form["Preenche dados do imóvel\nbedrooms, bathrooms, sqft_living\nfloors, grade, condition\nwaterfront, view, zipcode"]
            Btn["🟣 Prever Preço"]
        end

        subgraph Main["⬛ MainContent — Resultado"]
            Empty["Estado inicial\n'Pronto para avaliar'"]
            Result["Cartão de resultado\n💰 Preço estimado\n📊 Faixa P10–P90\n📍 vs mediana do bairro"]
            Cards["Cards de resumo\nQuartos · Banheiros\nÁrea útil · Grade"]
            Location["Localização\nBairro · ZIP · King County, WA"]
            Confidence["Confiança da previsão\n(largura do intervalo)"]
            WhyPrice["Por que este preço?\n(gráfico de contribuição por feature)"]
        end

        subgraph Chat["➡️ ChatPanel — Assistente IA"]
            Suggestions["Perguntas sugeridas\n'Por que esse preço?'\n'Como a localização afeta?'"]
            Input["Campo de texto livre"]
            Response["Resposta em linguagem natural\n(contextualizada com o imóvel avaliado)"]
        end
    end

    subgraph API["🔧 API (FastAPI)"]
        Predict["POST /predict\nXGBoost p50 + p10/p90\n< 100ms"]
        ChatAPI["POST /chat\nRAG (FAISS) + LLM\n~1–3s"]
    end

    Start --> Form
    Form --> Btn
    Btn -->|"JSON com features"| Predict
    Predict -->|"preço, p10, p90\nmediana do zipcode"| Result

    Result --> Cards
    Result --> Location
    Result --> Confidence
    Result --> WhyPrice

    Result -.->|"usuário clica em pergunta\nou digita livremente"| Suggestions
    Suggestions --> Input
    Input -->|"pergunta + contexto do imóvel\n+ previsão atual"| ChatAPI
    ChatAPI -->|"resposta em texto"| Response

    Empty -.->|"antes de prever"| Btn
```

---

## Diagrama Mermaid — Layout da Interface (desktop)

```mermaid
block-beta
    columns 3

    block:sidebar["⬅️ Sidebar\n(280px fixo)"]:1
        A["Detalhes do Imóvel\n\nQuartos / Banheiros\nÁrea interna (slider)\nAndares\nGrade (slider)\nCondição (slider)\nWaterfront (toggle)\nVista (slider)\nZipcode (select)\n\n[ Prever Preço ]"]
    end

    block:main["⬛ MainContent\n(flex-1)"]:1
        B["Estado vazio:\nPronto para avaliar\n\nApós previsão:\n$XXX,XXX\n$X — $Y (P10–P90)\n+X% vs mediana\n\nCards: quartos, área, grade\nLocalização: bairro + ZIP\nConfiança da previsão\nPor que este preço?"]
    end

    block:chat["➡️ ChatPanel\n(320px fixo)"]:1
        C["Assistente IA\n\nPerguntas sugeridas\n(contextualizam com\no imóvel avaliado)\n\n[Campo de pergunta]\n\nHistórico de conversa"]
    end
```

---

## Responsividade

A interface adapta os 3 painéis conforme o tamanho da tela:

```mermaid
flowchart LR
    subgraph Desktop["🖥️ Desktop (xl+)"]
        D1["Sidebar\nestático"]
        D2["MainContent\nflex-1"]
        D3["ChatPanel\nestático"]
    end

    subgraph Tablet["💻 Tablet / Laptop (md–xl)"]
        T1["MainContent\n(tela inteira)"]
        T2["Sidebar\n(overlay deslizante\npelo menu)"]
        T3["ChatPanel\n(overlay deslizante\npelo ícone)"]
    end

    subgraph Mobile["📱 Mobile (< md)"]
        M1["Bottom tab bar\n3 abas:\nFormulário | Resultado | Chat"]
    end
```

---

## Notas de Leitura

- O `POST /predict` é acionado **apenas** pelo botão "Prever Preço" — não há auto-predict ao alterar sliders (evita chamadas desnecessárias à API)
- O `POST /chat` carrega automaticamente o contexto do imóvel avaliado + a previsão atual — o usuário não precisa repassar os dados manualmente no chat
- As perguntas sugeridas no chat mudam conforme o estado: antes de prever (perguntas sobre o mercado), depois de prever (perguntas sobre o resultado específico)
- O toggle "Mostrar R$" converte os valores de US$ para BRL com câmbio aproximado — é uma referência de contexto, não dado financeiro oficial
