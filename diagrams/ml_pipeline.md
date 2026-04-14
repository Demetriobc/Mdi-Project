# Diagrama: Pipeline de Machine Learning

## Objetivo

Mostrar o pipeline completo de treinamento — desde os dados brutos até os artefatos salvos em `artifacts/model/`. O diagrama deixa visíveis as decisões de design: split temporal, treinamento paralelo de três modelos (p50, p10, p90), avaliação separada de baseline vs modelo final, e o que é salvo ao final.

## Blocos

| Bloco | Papel |
|---|---|
| **Dados brutos** | `kc_house_data.csv` + `zipcode_demographics.csv` — carregados e mergeados por zipcode |
| **Split temporal** | Cutoff jan/2015: treino = passado, teste = futuro — simula inferência real |
| **Feature Engineering** | `DerivedHousingFeatures` — cria 8 features derivadas sobre as 16 originais |
| **Preprocessador Ridge** | StandardScaler + OneHotEncoder para o baseline linear |
| **Preprocessador XGBoost** | ColumnTransformer com scaling e ordinal encoding |
| **Ridge baseline** | Regressão linear com L2 — referência de performance |
| **Holdout interno** | 10% do treino separado para early stopping do XGBoost |
| **XGBoost p50** | Modelo principal — previsão de ponto central |
| **XGBoost p10 / p90** | Quantile regression — limites do intervalo de confiança |
| **Avaliação** | Métricas em escala de dólares para baseline e XGBoost final |
| **SHAP** | Importâncias por valor SHAP no conjunto de teste |
| **Artefatos salvos** | model.joblib, preprocessor.joblib, metadata.json |

---

## Diagrama Mermaid

```mermaid
flowchart TD
    subgraph Dados["📦 Dados de Entrada"]
        KC["kc_house_data.csv\n21.613 transações"]
        Demo["zipcode_demographics.csv\n70 zipcodes"]
    end

    Merge["Merge por zipcode\n(LEFT JOIN)"]

    subgraph Split["✂️ Split Temporal"]
        Train["Treino\n< jan/2015\n17.148 registros"]
        Test["Teste\n≥ jan/2015\n4.287 registros"]
    end

    FE["DerivedHousingFeatures\n+8 features derivadas\n→ 24 features totais"]

    subgraph Baseline["📏 Ridge Baseline"]
        PreRidge["StandardScaler\n+ OneHotEncoder"]
        Ridge["Ridge α=10\n(log1p target)"]
    end

    subgraph XGBTraining["🌳 XGBoost"]
        Holdout["Holdout interno\n10% do treino\n(early stopping)"]
        PreXGB["ColumnTransformer\n(scaling + ordinal enc)"]
        XGB50["XGBRegressor\nobjective: reg:squarederror\n(ponto central — p50)"]
        XGB10["XGBRegressor\nobjective: reg:quantileerror\nquantile_alpha: 0.10"]
        XGB90["XGBRegressor\nobjective: reg:quantileerror\nquantile_alpha: 0.90"]
    end

    subgraph Eval["📊 Avaliação (conjunto de teste)"]
        MetricsB["Ridge\nRMSE $184k | MAE $108k\nR² 0.764 | MAPE 19.7%"]
        MetricsX["XGBoost\nRMSE $126k | MAE $62k\nR² 0.891 | MAPE 11.2%"]
        Coverage["Cobertura P10–P90\n~80% dos casos\nLargura média ~$194k"]
        SHAP["SHAP importance\ntop: lat, sqft_living, grade"]
    end

    subgraph Artifacts["💾 Artefatos Salvos"]
        ModelFile["house_price_model.joblib\n(pipeline p50 completo)"]
        PrepFile["preprocessor.joblib\n(pipeline sem modelo)"]
        Meta["metadata.json\nhiperparâmetros, métricas,\nimportâncias, medianas/zipcode"]
        P10File["model_p10.joblib"]
        P90File["model_p90.joblib"]
    end

    KC --> Merge
    Demo --> Merge
    Merge --> Split
    Train --> FE
    Test --> FE

    FE --> Baseline
    FE --> XGBTraining

    PreRidge --> Ridge
    Holdout -->|"n_estimators ideal"| XGB50
    PreXGB --> XGB50
    PreXGB --> XGB10
    PreXGB --> XGB90

    Ridge -->|"predict no teste"| MetricsB
    XGB50 -->|"predict no teste"| MetricsX
    XGB10 & XGB90 -->|"intervalo"| Coverage
    XGB50 -->|"SHAP values"| SHAP

    MetricsX --> Artifacts
    XGB50 --> ModelFile
    PreXGB --> PrepFile
    MetricsB & MetricsX & SHAP --> Meta
    XGB10 --> P10File
    XGB90 --> P90File
```

---

## Notas de Leitura

- O `DerivedHousingFeatures` é um `TransformerMixin` do scikit-learn — roda o mesmo código em treino e inferência, sem risco de divergir
- O early stopping usa RMSE em log-scale no holdout para determinar `n_estimators` ideal (cap: 600)
- Os três modelos XGBoost (p50, p10, p90) compartilham os mesmos hiperparâmetros base — só o `objective` e `quantile_alpha` diferem
- O `preprocessor.joblib` é salvo separado do modelo porque é necessário para extrair a matrix de features para cálculo de SHAP na inferência
- Toda a lógica está em `app/ml/train.py`; pode ser reproduzida com `make train`
