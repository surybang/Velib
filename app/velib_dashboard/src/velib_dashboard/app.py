"""Dashboard Vélib' — page d'accueil : carte temps réel."""

import folium
import streamlit as st
from streamlit_folium import st_folium

from velib_dashboard.api_client import get_city_stats, get_map_data, get_status
from velib_dashboard.style import CSS, VELIB_TEAL, marker_color, metric_card

st.set_page_config(
    page_title="Vélib' Dashboard",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center; padding: 1rem 0;'>
            <span style='font-size:2.5rem'>🚲</span>
            <h2 style='margin:0; color:white; font-size:1.3rem;'>Vélib' Dashboard</h2>
            <p style='color:#aaa; font-size:0.75rem; margin:0;'>Paris en temps réel</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    status = get_status()
    if status:
        st.markdown(
            f"""
            <div style='font-size:0.75rem; color:#aaa;'>
                <div>🕐 Collecte : {str(status.get('derniere_ingestion', ''))[:16]}</div>
                <div>📡 {status.get('stations_actives', '?')} stations actives</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("API injoignable")

# ── En-tête + métriques ──────────────────────────────────────────────────────
st.markdown("# 🚲 Vélib' Paris — Temps réel")

stats = get_city_stats()
if stats:
    temp = stats.get("temperature", "?")
    prec = stats.get("precipitation", 0) or 0
    meteo = "🌧️" if float(prec) > 0.5 else "☀️"
    st.markdown(
        f"""
        <div style='margin-bottom:1rem;'>
            <span class='meteo-badge'>{meteo} {temp}°C</span>
            <span class='meteo-badge'>💧 {prec} mm</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(
        metric_card(f"{stats.get('total_velos', '?'):,}", "Vélos disponibles"),
        unsafe_allow_html=True,
    )
    c2.markdown(
        metric_card(f"{stats.get('total_places', '?'):,}", "Places libres"),
        unsafe_allow_html=True,
    )
    c3.markdown(
        metric_card(f"{stats.get('occupation_moyenne', '?')}%", "Occupation moyenne"),
        unsafe_allow_html=True,
    )
    c4.markdown(
        metric_card(str(stats.get("stations_vides", "?")), "Stations vides", alert=True),
        unsafe_allow_html=True,
    )
    c5.markdown(
        metric_card(str(stats.get("stations_pleines", "?")), "Stations pleines"),
        unsafe_allow_html=True,
    )
else:
    st.error("Impossible de récupérer les statistiques. L'API est-elle démarrée ?")

# ── Carte ────────────────────────────────────────────────────────────────────
st.markdown("### Carte des stations")

stations = get_map_data()
if not stations:
    st.info("Aucune donnée de station disponible.")
else:
    m = folium.Map(location=[48.8566, 2.3522], zoom_start=13, tiles="CartoDB positron")

    for s in stations:
        if not s.get("lat") or not s.get("lon"):
            continue
        occ = s.get("occupancy_rate") or 0
        color = marker_color(occ)
        popup_html = f"""
        <div style='font-family:Inter,sans-serif; min-width:180px;'>
            <b style='color:{VELIB_TEAL};font-size:1rem;'>{s['station_name']}</b>
            <hr style='margin:4px 0; border-color:#eee;'>
            <div>🚲 {s.get('bikes_available', 0)} vélos
                 ({s.get('ebike', 0)}⚡ {s.get('mechanical', 0)}🔧)</div>
            <div>🅿️ {s.get('docks_available', 0)} places libres</div>
            <div>📊 Occupation : {occ}%</div>
            <div style='font-size:0.75rem; color:#999; margin-top:4px;'>
                {s.get('commune', '')} • {str(s.get('duedate_paris', ''))[:16]}
            </div>
        </div>
        """
        folium.CircleMarker(
            location=[s["lat"], s["lon"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            tooltip=s["station_name"],
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(m)

    st_folium(m, width="100%", height=520, returned_objects=[])

    st.markdown(
        """
        <div style='font-size:0.75rem;color:#999;margin-top:0.5rem;'>
            🟠 Vide &nbsp;·&nbsp; 🟡 Presque vide &nbsp;·&nbsp;
            🩵 Disponible &nbsp;·&nbsp; 🔵 Presque plein
        </div>
        """,
        unsafe_allow_html=True,
    )
