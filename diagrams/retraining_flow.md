# Diagrama: Fluxo de Reentreino

## Objetivo

Mostrar como o sistema evoluiria para incorporar novos dados e manter o modelo relevante ao longo do tempo. O diagrama cobre as três fases do ciclo de vida: detecção de que o reentreino é necessário, execução do pipeline de treinamento, e promoção segura do novo modelo para produção com critérios claros de aceite e rollback.

## Blocos

| Bloco | Papel |
|---|---|
| **Monitoramento contínuo** | Análise periódica da distribuição de features (PSI) e métricas de performance (MAPE) |
| **Gatilhos** | Condições quantitativas que acionam o pipeline de reentreino |
| **Coleta de dados** | Download incremental de novas transações + ground truth de preços realizados |
| **Pipeline de treino** | Mesmo pipeline do treino original — dados novos + histórico |
| **Avaliação do candidato** | Métricas do novo modelo comparadas com o modelo em produção |
| **Critérios de promoção** | Thresholds quantitativos + verificação em subgrupos críticos |
| **Deploy blue-green** | Switch de tráfego com fallback seguro para versão anterior |
| **Monitoramento pós-deploy** | Acompanhamento por 30 dias após a promoção |

---

## Diagrama Mermaid

```mermaid
flowchart TD
    subgraph Monitor["📡 Monitoramento Contínuo"]
        Logs[("PostgreSQL\nLogs de predição")]
        PSI["PSI por feature\n(semanal)"]
        MAPE_Prod["MAPE em produção\n(quando ground truth disponível)"]
    end

    subgraph Triggers["⚠️ Gatilhos de Reentreino"]
        T1{"PSI > 0.2\nem feature crítica?"}
        T2{"MAPE produção >\nMAPE referência + 5pp?"}
        T3{"Acumulou ≥ 5k\nnov. transações c/ target?"}
    end

    subgraph DataCollection["📦 Coleta de Dados"]
        NewData["Novas transações\nKing County Assessor"]
        HistData[("Dados históricos\nexistentes")]
        GroundTruth["Preços realizados\n(associados às predições)"]
        MergeData["Concatenar\nnov. + histórico"]
    end

    subgraph Training["🔁 Pipeline de Reentreino"]
        SplitNew["Split temporal\n(cutoff = data mais recente - 3 meses)"]
        FE_New["Feature Engineering\n(mesmo código)"]
        TrainNew["Treinar XGBoost\n(p50 + p10 + p90)"]
        EvalNew["Avaliar no holdout\ntemporal recente"]
    end

    subgraph Promotion["✅ Decisão de Promoção"]
        Compare{"Novo modelo ≥\nmodelo atual\nem todas métricas?"}
        Subgroups{"Performance OK\nem subgrupos críticos?\n(waterfront, grade≥10, >$1M)"}
        Approve["✅ Aprovado\npara produção"]
        Reject["❌ Rejeitado\nmanter modelo atual"]
    end

    subgraph Deploy["🚀 Deploy Blue-Green"]
        Build["Build Docker\nc/ novos artefatos"]
        Staging["Validação manual\nN imóveis de referência"]
        Switch["Switch de tráfego\n(Railway deploy)"]
        Watch["Monitoramento\n48h pós-switch"]
        Rollback["Rollback\n(deploy anterior)"]
        Stable["✅ Estável\n(v. anterior descartada)"]
    end

    Logs --> PSI
    Logs --> MAPE_Prod

    PSI --> T1
    MAPE_Prod --> T2
    NewData --> T3

    T1 -->|"sim"| DataCollection
    T2 -->|"sim"| DataCollection
    T3 -->|"sim"| DataCollection
    T1 -->|"não"| Monitor
    T2 -->|"não"| Monitor
    T3 -->|"não"| Monitor

    NewData --> MergeData
    HistData --> MergeData
    GroundTruth -.->|"análise de erro real"| MAPE_Prod

    MergeData --> SplitNew
    SplitNew --> FE_New
    FE_New --> TrainNew
    TrainNew --> EvalNew
    EvalNew --> Compare

    Compare -->|"sim"| Subgroups
    Compare -->|"não"| Reject

    Subgroups -->|"sim"| Approve
    Subgroups -->|"não"| Reject

    Approve --> Build
    Build --> Staging
    Staging --> Switch
    Switch --> Watch
    Watch -->|"problema detectado"| Rollback
    Watch -->|"estável"| Stable
    Rollback --> Monitor
```

---

## Notas de Leitura

- O ciclo de monitoramento é contínuo — os gatilhos verificam condições, não calendário
- A seta tracejada de `GroundTruth` para `MAPE_Prod` indica que o loop de avaliação real só é possível quando preços realizados estão disponíveis
- "Subgrupos críticos" são imóveis waterfront, grade ≥ 10 e preço > $1M — segmentos com poucos dados de treino e maior risco de regressão
- O rollback no Railway é feito via interface de deployments — qualquer build anterior pode ser restaurado em < 2 minutos
- Documentação detalhada: [`docs/4-aprendizado-continuo.md`](../docs/4-aprendizado-continuo.md)
