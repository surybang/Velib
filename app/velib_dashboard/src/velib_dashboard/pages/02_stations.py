"""Fiche station : état actuel et historique."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from velib_dashboard.api_client import (
    get_station_current,
    get_station_history,
    get_stations,
)
from velib_dashboard.style import CSS, VELIB_DARK, VELIB_ORANGE, VELIB_TEAL, metric_card

st.set_page_config(page_title="Station · Vélib'", page_icon="📍", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("# 📍 Fiche station")

stations = get_stations()
if not stations:
    st.error("API injoignable ou aucune station disponible.")
    st.stop()

# ── Sélecteurs ───────────────────────────────────────────────────────────────
options = {f"{s['station_name']} ({s['commune']})": s["stationcode"] for s in stations}
choix = st.selectbox("Station", list(options.keys()))
code = options[choix]
hours = st.slider("Historique (heures)", 1, 168, 24)

# ── État actuel ──────────────────────────────────────────────────────────────
current = get_station_current(code)
if current:
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        metric_card(str(current.get("bikes_available", "?")), "Vélos disponibles"),
        unsafe_allow_html=True,
    )
    c2.markdown(
        metric_card(str(current.get("docks_available", "?")), "Places libres"),
        unsafe_allow_html=True,
    )
    c3.markdown(
        metric_card(
            f"{current.get('mechanical', 0)}🔧 {current.get('ebike', 0)}⚡", "Méca / Élec"
        ),
        unsafe_allow_html=True,
    )
    occ = current.get("occupancy_rate", 0) or 0
    alert = occ == 0 or occ >= 95
    c4.markdown(
        metric_card(f"{occ}%", "Occupation", alert=alert), unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div style='font-size:0.8rem;color:#999;margin-top:0.5rem;'>
            📍 {current.get('commune', '')} •
            Capacité {current.get('capacity', '?')} •
            Mis à jour {str(current.get('duedate_paris', ''))[:16]}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Historique ───────────────────────────────────────────────────────────────
st.markdown("### Historique")

history = get_station_history(code, hours)
if not history:
    st.info("Pas de données sur cette période.")
else:
    df = pd.DataFrame(history)
    df["ts"] = pd.to_datetime(df["ts"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["ts"],
            y=df["bikes_available"],
            name="Vélos disponibles",
            line=dict(color=VELIB_TEAL, width=2),
            fill="tozeroy",
            fillcolor="rgba(91,200,200,0.15)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["ts"],
            y=df["docks_available"],
            name="Places libres",
            line=dict(color=VELIB_DARK, width=1.5, dash="dot"),
        )
    )
    fig.update_layout(
        template="plotly_white",
        font_family="Inter",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
        height=350,
        xaxis_title="",
        yaxis_title="Nombre",
    )
    st.plotly_chart(fig, width='stretch')

    # Occupation en barres, orange si rupture
    fig2 = go.Figure(
        go.Bar(
            x=df["ts"],
            y=df["occupancy_rate"],
            marker_color=[
                VELIB_ORANGE if (v or 0) == 0 else VELIB_TEAL
                for v in df["occupancy_rate"]
            ],
        )
    )
    fig2.update_layout(
        template="plotly_white",
        font_family="Inter",
        height=200,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(title="Occupation (%)", range=[0, 105]),
        showlegend=False,
    )
    st.plotly_chart(fig2, width='stretch')
