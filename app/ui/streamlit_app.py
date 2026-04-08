"""
Interface principal do House Price Copilot.

Consome a API FastAPI — nenhuma lógica de ML ou RAG aqui.
Toda a inteligência fica nos serviços da API.

Layout:
  Sidebar  → formulário de entrada do imóvel
  Main     → preço previsto + contexto + explicação AI + chat
"""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

# ── Configuração de página ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="House Price Copilot",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")


# ── Inicialização do session state ────────────────────────────────────────────
def _init_session_state() -> None:
    defaults = {
        "prediction": None,
        "explanation": None,
        "chat_history": [],       # lista de {"role": "user"|"assistant", "content": str}
        "api_ok": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_session_state()


# ── CSS personalizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    .price-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 1rem;
        border: 1px solid #e94560;
    }
    .price-label { color: #a0aec0; font-size: 0.9rem; letter-spacing: 2px; text-transform: uppercase; }
    .price-value { color: #ffffff; font-size: 3rem; font-weight: 800; margin: 0.5rem 0; }
    .price-sub   { color: #68d391; font-size: 1rem; }
    .chat-user     { background: #2d3748; border-radius: 12px 12px 2px 12px; padding: 0.8rem 1rem; margin: 0.5rem 0; }
    .chat-assistant{ background: #1a365d; border-radius: 12px 12px 12px 2px; padding: 0.8rem 1rem; margin: 0.5rem 0; border-left: 3px solid #4299e1; }
    .feature-tag { background: #2b6cb0; color: white; border-radius: 6px; padding: 2px 8px; font-size: 0.8rem; margin: 2px; display: inline-block; }
    .section-header { border-bottom: 2px solid #4299e1; padding-bottom: 0.3rem; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)


# ── Funções de API ────────────────────────────────────────────────────────────
def _call_api(method: str, path: str, payload: dict | None = None) -> dict | None:
    """Wrapper genérico para chamadas à API com tratamento de erro."""
    try:
        url = f"{API_BASE_URL}{path}"
        if method == "GET":
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error(
            f"API indisponível em `{API_BASE_URL}`. "
            "Execute `python -m uvicorn app.api.main:app --port 8001` no terminal."
        )
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Erro da API ({e.response.status_code}): {e.response.text[:300]}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
        return None


def check_api_health() -> bool:
    data = _call_api("GET", "/health")
    return data is not None and data.get("status") in ("ok", "degraded")


def predict(house_data: dict) -> dict | None:
    return _call_api("POST", "/predict", house_data)


def get_explanation(context: dict) -> dict | None:
    return _call_api("POST", "/chat/explain", context)


def send_chat(message: str, context: dict | None, history: list) -> dict | None:
    payload = {
        "message": message,
        "prediction_context": context,
        "conversation_history": history,
    }
    return _call_api("POST", "/chat", payload)


# ── Formulário de entrada ─────────────────────────────────────────────────────
ZIPCODES = {
    "98103 — Seattle (Fremont/Wallingford)": "98103",
    "98107 — Seattle (Ballard)": "98107",
    "98115 — Seattle (Ravenna)": "98115",
    "98117 — Seattle (Crown Hill)": "98117",
    "98112 — Seattle (Capitol Hill)": "98112",
    "98119 — Seattle (Queen Anne)": "98119",
    "98105 — Seattle (University District)": "98105",
    "98122 — Seattle (Central District)": "98122",
    "98126 — Seattle (West Seattle)": "98126",
    "98133 — Seattle (Broadview)": "98133",
    "98004 — Bellevue": "98004",
    "98006 — Bellevue (SE)": "98006",
    "98033 — Kirkland": "98033",
    "98034 — Kirkland (Norte)": "98034",
    "98052 — Redmond": "98052",
    "98039 — Medina (Luxo)": "98039",
    "98040 — Mercer Island": "98040",
    "98074 — Sammamish": "98074",
    "98059 — Renton (NE)": "98059",
    "98056 — Renton": "98056",
    "98027 — Issaquah": "98027",
    "98029 — Issaquah (Highlands)": "98029",
    "98072 — Woodinville": "98072",
    "98001 — Auburn": "98001",
    "98003 — Federal Way": "98003",
    "98030 — Kent": "98030",
    "98042 — Kent/Covington": "98042",
}

ZIPCODE_COORDS = {
    "98103": (47.660, -122.344), "98107": (47.669, -122.383),
    "98115": (47.682, -122.318), "98117": (47.689, -122.370),
    "98112": (47.627, -122.295), "98119": (47.640, -122.361),
    "98105": (47.663, -122.298), "98122": (47.608, -122.296),
    "98126": (47.555, -122.378), "98133": (47.718, -122.354),
    "98004": (47.610, -122.200), "98006": (47.573, -122.153),
    "98033": (47.681, -122.198), "98034": (47.712, -122.202),
    "98052": (47.670, -122.118), "98039": (47.623, -122.235),
    "98040": (47.571, -122.222), "98074": (47.617, -122.043),
    "98059": (47.490, -122.138), "98056": (47.500, -122.189),
    "98027": (47.528, -122.029), "98029": (47.565, -122.019),
    "98072": (47.754, -122.153), "98001": (47.306, -122.214),
    "98003": (47.322, -122.318), "98030": (47.380, -122.234),
    "98042": (47.368, -122.108),
}


def render_sidebar() -> dict | None:
    """Renderiza o formulário lateral e retorna os dados do imóvel."""
    with st.sidebar:
        st.markdown("## 🏠 Dados do Imóvel")
        st.caption("King County, Washington — dataset 2014–2015")
        st.divider()

        # Localização
        st.markdown("**Localização**")
        zipcode_label = st.selectbox("Zipcode / Bairro", list(ZIPCODES.keys()), index=0)
        zipcode = ZIPCODES[zipcode_label]
        lat, long = ZIPCODE_COORDS.get(zipcode, (47.5, -122.3))

        st.divider()

        # Características principais
        st.markdown("**Características principais**")
        col1, col2 = st.columns(2)
        with col1:
            bedrooms = st.number_input("Quartos", min_value=1, max_value=10, value=3)
            sqft_living = st.number_input("Área útil (sqft)", min_value=300, max_value=12000, value=1800, step=100)
            grade = st.slider("Grade (qualidade)", min_value=3, max_value=13, value=7,
                              help="7=padrão | 8-9=bom | 10-11=premium | 12-13=luxo")
        with col2:
            bathrooms = st.number_input("Banheiros", min_value=0.5, max_value=8.0, value=2.0, step=0.5)
            floors = st.selectbox("Andares", [1.0, 1.5, 2.0, 2.5, 3.0], index=0)
            condition = st.slider("Condição", min_value=1, max_value=5, value=3,
                                  help="1=ruim | 3=bom (média) | 5=excelente")

        st.divider()

        # Vista e especiais
        st.markdown("**Vista e diferenciais**")
        col3, col4 = st.columns(2)
        with col3:
            view = st.slider("Qualidade da vista", 0, 4, 0, help="0=nenhuma | 4=excelente")
        with col4:
            waterfront = st.checkbox("Frente para a água", value=False)

        # Campos avançados
        with st.expander("Campos avançados"):
            yr_built = st.number_input("Ano de construção", min_value=1900, max_value=2015, value=1990)
            yr_renovated = st.number_input("Ano de renovação (0 = nunca)", min_value=0, max_value=2015, value=0)
            sqft_lot = st.number_input("Área do lote (sqft)", min_value=500, max_value=500000, value=5000, step=500)
            sqft_above = st.number_input("Área acima do solo (sqft)", min_value=300, max_value=12000,
                                         value=min(sqft_living, sqft_living), step=100)
            sqft_basement = max(0, sqft_living - sqft_above)
            st.caption(f"Porão calculado automaticamente: {sqft_basement} sqft")
            sqft_living15 = st.number_input("Área útil vizinhos (sqft)", min_value=300, max_value=8000,
                                             value=sqft_living, step=100,
                                             help="Área útil média dos 15 imóveis vizinhos")
            sqft_lot15 = st.number_input("Lote vizinhos (sqft)", min_value=500, max_value=500000,
                                          value=sqft_lot, step=500)

        st.divider()

        predict_btn = st.button("Prever Preço", type="primary", use_container_width=True)

        if predict_btn:
            return {
                "bedrooms": int(bedrooms),
                "bathrooms": float(bathrooms),
                "sqft_living": int(sqft_living),
                "sqft_lot": int(sqft_lot),
                "floors": float(floors),
                "waterfront": int(waterfront),
                "view": int(view),
                "condition": int(condition),
                "grade": int(grade),
                "sqft_above": int(min(sqft_above, sqft_living)),
                "sqft_basement": int(sqft_basement),
                "yr_built": int(yr_built),
                "yr_renovated": int(yr_renovated),
                "zipcode": zipcode,
                "lat": float(lat),
                "long": float(long),
                "sqft_living15": int(sqft_living15),
                "sqft_lot15": int(sqft_lot15),
            }

    return None


# ── Componentes de resultado ──────────────────────────────────────────────────

def render_price_card(prediction: dict) -> None:
    price = prediction["predicted_price_formatted"]
    zipcode = prediction["zipcode"]
    pct = prediction.get("price_vs_median_pct")
    median = prediction.get("zipcode_median_price")

    if pct is not None:
        sign = "+" if pct >= 0 else ""
        sub_text = f"{sign}{pct:.1f}% vs mediana do zipcode (US$ {median:,.0f})"
        sub_color = "#68d391" if pct >= 0 else "#fc8181"
    else:
        sub_text = f"Zipcode {zipcode}"
        sub_color = "#a0aec0"

    st.markdown(f"""
    <div class="price-card">
        <p class="price-label">Preço Estimado · Zipcode {zipcode}</p>
        <p class="price-value">{price}</p>
        <p class="price-sub" style="color:{sub_color}">{sub_text}</p>
    </div>
    """, unsafe_allow_html=True)


def render_metrics_row(prediction: dict) -> None:
    cols = st.columns(4)
    with cols[0]:
        st.metric("Quartos", prediction["bedrooms"])
    with cols[1]:
        st.metric("Banheiros", prediction["bathrooms"])
    with cols[2]:
        st.metric("Área útil", f"{prediction['sqft_living']:,} sqft")
    with cols[3]:
        grade = prediction["grade"]
        grade_labels = {7: "Padrão", 8: "Bom", 9: "Ótimo", 10: "Premium", 11: "Luxo", 12: "Luxo+", 13: "Luxo++"}
        label = grade_labels.get(grade, f"Grade {grade}")
        st.metric("Grade", f"{grade} — {label}")


def render_feature_importance(prediction: dict) -> None:
    top = prediction.get("top_features", {})
    if not top:
        return

    st.markdown("#### Top Features por Importância (SHAP)")
    feature_labels = {
        "lat": "Latitude (localização N-S)",
        "sqft_living": "Área útil",
        "grade": "Qualidade de construção",
        "long": "Longitude (localização L-O)",
        "sqft_living15": "Área útil dos vizinhos",
        "sqft_above": "Área acima do solo",
        "zipcode": "Zipcode",
        "house_age": "Idade da casa",
        "bathrooms": "Banheiros",
        "bedrooms": "Quartos",
        "living_lot_ratio": "Ratio área/lote",
        "bath_bed_ratio": "Ratio banheiros/quartos",
    }

    import pandas as pd
    df = pd.DataFrame(
        [{"Feature": feature_labels.get(k, k), "Importância": v}
         for k, v in list(top.items())[:6]]
    ).sort_values("Importância", ascending=True)

    st.bar_chart(df.set_index("Feature"), horizontal=True, height=220)


def render_explanation(explanation_text: str, sources: list[str], llm_ok: bool) -> None:
    st.markdown("#### Explicação do Modelo")
    if not llm_ok:
        st.warning(explanation_text)
    else:
        st.info(explanation_text)
        if sources:
            with st.expander("Fontes consultadas"):
                for s in sources:
                    st.caption(f"📄 {s}")


def render_chat(prediction_context: dict | None) -> None:
    st.markdown("---")
    st.markdown("### 💬 Pergunte ao Copiloto")
    st.caption(
        "Faça perguntas sobre a previsão: "
        '"Por que essa casa ficou cara?", "Essa previsão é confiável?", '
        '"Como esse zipcode se compara?", "Quais são as limitações?"'
    )

    # Histórico
    for msg in st.session_state.chat_history:
        css_class = "chat-user" if msg["role"] == "user" else "chat-assistant"
        icon = "👤" if msg["role"] == "user" else "🤖"
        st.markdown(
            f'<div class="{css_class}">{icon} {msg["content"]}</div>',
            unsafe_allow_html=True,
        )

    # Input
    with st.form("chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_input = st.text_input(
                "Sua pergunta",
                placeholder="Ex: Por que essa casa ficou acima da média do zipcode?",
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("Enviar", use_container_width=True)

    if submitted and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.spinner("Consultando o copiloto..."):
            response = send_chat(
                message=user_input,
                context=prediction_context,
                history=st.session_state.chat_history[:-1],
            )

        if response:
            answer = response.get("answer", "Sem resposta.")
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
        else:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "Não foi possível obter uma resposta. Verifique a API e a chave OpenAI."
            })

        st.rerun()

    if st.session_state.chat_history:
        if st.button("Limpar conversa", type="secondary"):
            st.session_state.chat_history = []
            st.rerun()


# ── Tela principal ────────────────────────────────────────────────────────────

def render_welcome() -> None:
    st.markdown("""
    <div style="text-align: center; padding: 3rem 1rem;">
        <h1 style="font-size: 2.5rem;">🏠 House Price Copilot</h1>
        <p style="font-size: 1.2rem; color: #a0aec0; max-width: 600px; margin: 1rem auto;">
            Previsão de preços de imóveis em <strong>King County, WA</strong>
            com <strong>Machine Learning</strong> + <strong>IA Generativa</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🤖 ML Core\nModelo XGBoost treinado em 21k+ vendas reais. R² ≈ 0.89.")
    with col2:
        st.markdown("### 🔍 RAG\nKnowledge base vetorial com contexto de mercado, bairros e features.")
    with col3:
        st.markdown("### 💬 Chat\nExplicações em linguagem natural e respostas contextualizadas.")

    st.divider()
    st.markdown(
        "**Como usar:** preencha os dados do imóvel no painel esquerdo "
        "e clique em **Prever Preço**."
    )


def main() -> None:
    # Header
    st.markdown(
        "<h2 style='margin-bottom:0'>🏠 House Price Copilot</h2>"
        "<p style='color:#a0aec0;margin-top:0'>King County, WA · XGBoost + RAG + LLM</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # Formulário na sidebar
    house_data = render_sidebar()

    # Ação: nova predição
    if house_data:
        with st.spinner("Calculando preço..."):
            result = predict(house_data)

        if result:
            st.session_state.prediction = result
            st.session_state.explanation = None
            st.session_state.chat_history = []

            # Gera explicação automática
            with st.spinner("Gerando explicação..."):
                expl = get_explanation(result)
            if expl:
                st.session_state.explanation = expl

    # Renderiza resultado se existir
    if st.session_state.prediction:
        pred = st.session_state.prediction
        expl = st.session_state.explanation

        render_price_card(pred)
        render_metrics_row(pred)

        st.divider()

        col_left, col_right = st.columns([3, 2])
        with col_left:
            if expl:
                render_explanation(
                    expl.get("answer", ""),
                    expl.get("sources", []),
                    expl.get("llm_available", False),
                )
        with col_right:
            render_feature_importance(pred)

        # Chat
        prediction_context = {
            "predicted_price": pred["predicted_price"],
            "predicted_price_formatted": pred["predicted_price_formatted"],
            "zipcode": pred["zipcode"],
            "sqft_living": pred["sqft_living"],
            "bedrooms": pred["bedrooms"],
            "bathrooms": pred["bathrooms"],
            "grade": pred["grade"],
            "condition": pred["condition"],
            "top_features": pred.get("top_features", {}),
            "zipcode_median_price": pred.get("zipcode_median_price"),
            "price_vs_median_pct": pred.get("price_vs_median_pct"),
        }
        render_chat(prediction_context)

    else:
        render_welcome()


if __name__ == "__main__":
    main()
