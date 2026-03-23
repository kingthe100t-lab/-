import streamlit as st
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math
import numpy as np
from scipy.interpolate import interp1d
from google import genai
import pandas as pd
import datetime

st.set_page_config(layout="wide", page_title="SKY-DIRECTOR PRO")
st.markdown("<h1 style='color: #0088ff;'>🛫 SKY-DIRECTOR PRO</h1>", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv("spots.csv")
    df["緯度"] = pd.to_numeric(df["緯度"], errors="coerce")
    df["経度"] = pd.to_numeric(df["経度"], errors="coerce")
    df = df.dropna(subset=["緯度", "経度"])
    return df

try:
    df_spots = load_data()
except FileNotFoundError:
    st.error("🚨 エラー: GitHubに `spots.csv` がアップロードされていません！")
    st.stop()

# --- セッション状態の初期化 ---
if "selected_spot" not in st.session_state:
    st.session_state.selected_spot = df_spots.iloc[0]["スポット"]
if "plane_lat" not in st.session_state:
    st.session_state.plane_lat = 33.585
if "plane_lon" not in st.session_state:
    st.session_state.plane_lon = 130.445
if "processed_click" not in st.session_state:
    st.session_state.processed_click = None

if "map_center" not in st.session_state:
    st.session_state.map_center = [33.560, 130.460]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 12

metrics_placeholder = st.empty()
st.markdown("---")

# --- 🎯 ターゲット・フィルター機能 ---
filter_rwy = st.radio("🎯 運用滑走路でスポットを絞り込み", ["すべて", "16", "34"], horizontal=True)

if filter_rwy != "すべて":
    filtered_df = df_spots[df_spots['RWY'].str.contains(filter_rwy, na=False)]
else:
    filtered_df = df_spots

if filtered_df.empty or st.session_state.selected_spot not in filtered_df["スポット"].values:
    if not filtered_df.empty:
        st.session_state.selected_spot = filtered_df.iloc[0]["スポット"]
    else:
        st.error("🚨 選択された条件に合うスポットがありません。")
        st.stop()

spot_data = filtered_df[filtered_df['スポット'] == st.session_state.selected_spot].iloc[0]

st.info("👆 **【操作方法】** 地図上の「カメラピン」をタッチで撮影場所変更。**道や空き地をタッチすると、そこに被写体（✈️）が瞬間移動します！**")

col_map, col_tactical = st.columns([2, 1.2])

with col_map:
    st.markdown("##### ⚙️ シミュレーション・コントロール")
    col_s1, col_s2 = st.columns([1, 1.5])
    
    with col_s1:
        sim_day = st.radio("📅 予定日", ["本日", "明日"], horizontal=True)
    with col_s2:
        sim_hour = st.slider("☀️ タイムライン（時刻）", 7, 22, 12)

    if 7 <= sim_hour <= 11:
        wind_dir, wind_speed, current_rwy = 160, 6, "16"
    elif 12 <= sim_hour <= 16:
        wind_dir, wind_speed, current_rwy = 330, 12, "34"
    else:
        wind_dir, wind_speed, current_rwy = 340, 18, "34"

    plane_heading = 156 if current_rwy == "16" else 336

    with metrics_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("風向", f"{wind_dir}°")
        c2.metric("風速", f"{wind_speed} kt")
        c3.metric("運用滑走路", f"RWY {current_rwy}")
        c4.metric("予定日時", f"{sim_day} {sim_hour}:00")

    if "main_map" in st.session_state and st.session_state["main_map"] is not None:
        cached_map = st.session_state["main_map"]
        if cached_map.get("center") and cached_map.get("zoom"):
            st.session_state.map_center = [cached_map["center"]["lat"], cached_map["center"]["lng"]]
            st.session_state.map_zoom = cached_map["zoom"]

    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    
    wind_html = f'<div style="font-size: 35px; color: #00f0ff; text-shadow: 2px 2px 4px #000; transform: rotate({wind_dir}deg); transform-origin: center;">⬇</div>'
    folium.Marker(
        [33.585, 130.445],
        tooltip=f"💨 風向き: {wind_dir}° ({wind_speed}kt)",
        icon=folium.DivIcon(html=wind_html)
    ).add_to(m)

    rwy16_pos = np.array([33.5955, 130.4439])
    rwy34_pos = np.array([33.5750, 130.4581])
    
    def create_smooth_path(points, num_points=120):
        lats, lons = [p[0] for p in points], [p[1] for p in points]
        t = np.zeros(len(points))
        for i in range(1, len(points)):
            t[i] = t[i-1] + math.sqrt((lats[i]-lats[i-1])**2 + (lons[i]-lons[i-1])**2)
        t /= t[-1] 
        return [[float(lat), float(lon)] for lat, lon in zip(interp1d(t, lats, kind='cubic')(np.linspace(0, 1, num_points)), interp1d(t, lons, kind='cubic')(np.linspace(0, 1, num_points)))]

    if current_rwy == "16":
        path_coords = create_smooth_path([[33.720, 130.340], [33.660, 130.390], [33.620, 130.425], [rwy16_pos[0], rwy16_pos[1]]], 50)
        AntPath(locations=path_coords, delay=800, weight=6, color="#00f0ff", pulse_color="#ffffff", tooltip="RWY16 アプローチ・ルート").add_to(m)
    else:
        faf_pos = [33.550558624462184, 130.47508525096282]
        curve_points = [
            [33.6800, 130.3000], [33.6200, 130.3500], [33.5700, 130.3950], 
            [33.5400, 130.4150], [33.5180, 130.4400], [33.5250, 130.4650], 
            faf_pos
        ]
        path_coords = create_smooth_path(curve_points, 120) + [faf_pos, [rwy34_pos[0], rwy34_pos[1]]]
        AntPath(locations=path_coords, delay=800, weight=6, color="#0088ff", pulse_color="#ffffff", tooltip="RWY34 アプローチ・ルート").add_to(m)
        folium.CircleMarker(faf_pos, radius=6, color="#00ff00", fill=True, tooltip="ファイナル合流点").add_to(m)

    sun_azimuth = 180 + (sim_hour - 12) * 15
    sun_azimuth_rad = math.radians(sun_azimuth)
    
    x1 = 50 + 50 * math.sin(sun_azimuth_rad)
    y1 = 50 - 50 * math.cos(sun_azimuth_rad)
    x2 = 50 - 50 * math.sin(sun_azimuth_rad)
    y2 = 50 + 50 * math.cos(sun_azimuth_rad)

    plane_rot = plane_heading 
    plane_pos = [st.session_state.plane_lat, st.session_state.plane_lon]

    # ▼ 修正：モバイル端末のブロックを貫通するため、すべてのタグに pointer-events: none を強制注入
    # ▼ 修正：アイコンを洗練されたジェット旅客機のシルエットに変更
    plane_svg = f"""
    <style>
    .ghost-marker {{
        pointer-events: none !important;
        background: transparent !important;
        border: none !important;
        touch-action: none !important;
    }}
    </style>
    <svg width="4000" height="4000" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" style="pointer-events: none !important; touch-action: none !important;">
        <defs style="pointer-events: none !important;">
            <linearGradient id="sunLight" x1="{x1}%" y1="{y1}%" x2="{x2}%" y2="{y2}%" style="pointer-events: none !important;">
                <stop offset="0%" stop-color="#FF7700" stop-opacity="0.6" />
                <stop offset="40%" stop-color="#FF8800" stop-opacity="0.4" />
                <stop offset="55%" stop-color="#FF9900" stop-opacity="0.0" />
                <stop offset="100%" stop
