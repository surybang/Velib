"""Tendances : occupation par commune et répartition mécanique/électrique."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from velib_dashboard.api_client import get_by_commune, get_map_data
from velib_dashboard.style import CSS, VELIB_DARK, VELIB_TEAL

st.set_page_config(page_title="Tendances · Vélib'", page_icon="📈", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("# 📈 Tendances Paris")

# ── Occupation par commune ───────────────────────────────────────────────────
st.markdown("### Occupation par commune")

communes = get_by_commune()
if communes:
    df = pd.DataFrame(communes).sort_values("occupation_moyenne")
    fig = px.bar(
        df,
        x="occupation_moyenne",
        y="commune",
        orientation="h",
        color="occupation_moyenne",
        color_continuous_scale=[[0, "#E8834A"], [0.5, VELIB_TEAL], [1, "#3D6B8C"]],
        labels={"occupation_moyenne": "Occupation (%)", "commune": ""},
        hover_data=["nb_stations", "total_velos", "stations_vides"],
        template="plotly_white",
    )
    fig.update_layout(
        coloraxis_showscale=False,
        font_family="Inter",
        margin=dict(l=0, r=0, t=10, b=0),
        height=max(300, len(df) * 28),
    )
    st.plotly_chart(fig, width='stretch')
else:
    st.info("Aucune donnée par commune.")

# ── Répartition mécanique / électrique ───────────────────────────────────────
st.markdown("### Répartition mécanique vs électrique")

stations = get_map_data()
if stations:
    df = pd.DataFrame(stations)
    total_meca = int(df["mechanical"].fillna(0).sum())
    total_elec = int(df["ebike"].fillna(0).sum())
    total = total_meca + total_elec

    col1, col2 = st.columns([1, 2])
    with col1:
        fig_pie = go.Figure(
            go.Pie(
                labels=["Mécanique 🔧", "Électrique ⚡"],
                values=[total_meca, total_elec],
                marker_colors=[VELIB_TEAL, VELIB_DARK],
                hole=0.45,
                textinfo="label+percent",
            )
        )
        fig_pie.update_layout(
            showlegend=False,
            font_family="Inter",
            margin=dict(l=0, r=0, t=10, b=0),
            height=280,
        )
        st.plotly_chart(fig_pie, width='stretch')

    with col2:
        ratio = (total_elec / total * 100) if total else 0
        st.markdown(
            f"""
            <div style='padding:1.5rem;'>
                <div style='font-size:2rem;font-weight:700;color:{VELIB_TEAL};'>
                    {total_elec:,}
                </div>
                <div style='color:#777;font-size:0.85rem;'>vélos électriques</div>
                <div style='font-size:2rem;font-weight:700;color:{VELIB_DARK};margin-top:1rem;'>
                    {total_meca:,}
                </div>
                <div style='color:#777;font-size:0.85rem;'>vélos mécaniques</div>
                <div style='margin-top:1rem;color:#777;font-size:0.85rem;'>
                    Part électrique : {ratio:.0f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.info("Aucune donnée de station.")
