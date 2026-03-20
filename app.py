import streamlit as st
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math
import numpy as np
from scipy.interpolate import interp1d
import google.generativeai as genai

st.set_page_config(layout="wide", page_title="SKY-DIRECTOR PRO")
st.markdown("<h1 style='color: #0088ff;'>🛫 SKY-DIRECTOR PRO: FUK Tactical Map</h1>", unsafe_allow_html=True)

FUK_SPOTS = [
    {"name": "大井中央公園エンド", "lat": 33.5960, "lon": 130.4460},
    {"name": "1番スポットの丘", "lat": 33.5938, "lon": 130.4510},
    {"name": "西月隈歩道橋", "lat": 33.5695, "lon": 130.4578},
    {"name": "ひこうきの丘", "lat": 33.5752, "lon": 130.4610},
    {"name": "春日公園", "lat": 33.5285, "lon": 130.4705},
    {"name": "御笠川ファイナル会合点", "lat": 33.5350, "lon": 130.4680},
    {"name": "ルミエール付近交差点", "lat": 33.5276, "lon": 130.4448},
    {"name": "井野山展望台", "lat": 33.5875, "lon": 130.5085}
]

def create_smooth_path(points, num_points=120):
    lats, lons = [p[0] for p in points], [p[1] for p in points]
    t = np.zeros(len(points))
    for i in range(1, len(points)):
        t[i] = t[i-1] + math.sqrt((lats[i]-lats[i-1])**2 + (lons[i]-lons[i-1])**2)
    t /= t[-1] 
    return [[float(lat), float(lon)] for lat, lon in zip(interp1d(t, lats, kind='cubic')(np.linspace(0, 1, num_points)), interp1d(t, lons, kind='cubic')(np.linspace(0, 1, num_points)))]

selected_spot_name = st.selectbox("▼ ターゲット・スポット選択", [s["name"] for s in FUK_SPOTS])

# 運用時間 7:00 〜 22:00
sim_hour = st.slider("▼ タイムライン操作", 7, 22, 12)

if 7 <= sim_hour <= 11:
    wind_dir, wind_speed, current_rwy = 160, 6, "16"
elif 12 <= sim_hour <= 16:
    wind_dir, wind_speed, current_rwy = 330, 12, "34"
else:
    wind_dir, wind_speed, current_rwy = 340, 18, "34"

c1, c2, c3, c4 = st.columns(4)
c1.metric("風向", f"{wind_dir}°")
c2.metric("風速", f"{wind_speed} kt")
c3.metric("運用滑走路", f"RWY {current_rwy}")
c4.metric("時刻", f"{sim_hour}:00")

col_map, col_tactical = st.columns([2, 1.2])

with col_map:
    m = folium.Map(location=[33.560, 130.410], zoom_start=12, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    
    rwy16_pos = np.array([33.5969, 130.4432])
    rwy34_pos = np.array([33.5750, 130.4582])
    
    if current_rwy == "16":
        path_coords = create_smooth_path([[33.720, 130.340], [33.660, 130.390], [33.620, 130.425], [rwy16_pos[0], rwy16_pos[1]]], 50)
        AntPath(locations=path_coords, delay=800, weight=6, color="#00f0ff", pulse_color="#ffffff").add_to(m)
    else:
        # マスターの青色ルート
        rwy_vec = rwy16_pos - rwy34_pos
        faf_pos = rwy34_pos - rwy_vec * 1.8 
        curve_points = [
            [33.6800, 130.3000], [33.6200, 130.3500], [33.5700, 130.3950], 
            [33.5400, 130.4150], [33.5180, 130.4350], [33.5150, 130.4550], 
            [faf_pos[0], faf_pos[1]]
        ]
        path_coords = create_smooth_path(curve_points, 120) + [[faf_pos[0], faf_pos[1]], [rwy34_pos[0], rwy34_pos[1]]]
        AntPath(locations=path_coords, delay=800, weight=6, color="#0088ff", pulse_color="#ffffff").add_to(m)
        folium.CircleMarker([faf_pos[0], faf_pos[1]], radius=6, color="#00ff00", fill=True, tooltip="御笠川 ファイナル合流点").add_to(m)

    for spot in FUK_SPOTS:
        is_selected = (spot["name"] == selected_spot_name)
        folium.Marker([spot["lat"], spot["lon"]], tooltip=spot["name"], icon=folium.Icon(color="green" if is_selected else "red", icon="camera", prefix="fa")).add_to(m)

    st_folium(m, use_container_width=True, height=600)

with col_tactical:
    selected_lat = next(s["lat"] for s in FUK_SPOTS if s["name"] == selected_spot_name)
    selected_lon = next(s["lon"] for s in FUK_SPOTS if s["name"] == selected_spot_name)
    
    st.markdown(f"### 🌐 拡大サテライト: {selected_spot_name}")
    ms = folium.Map(location=[selected_lat, selected_lon], zoom_start=18, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri", control_scale=True)
    folium.Marker([selected_lat, selected_lon], icon=folium.Icon(color="green", icon="camera", prefix="fa")).add_to(ms)
    st_folium(ms, use_container_width=True, height=250)
    
    st.markdown("### 🤖 TACTICAL A.I.")
    if st.button("⚡ ブリーフィングをリクエスト", type="primary", use_container_width=True):
        with st.spinner("ANALYZING..."):
            try:
                # サーバーのシークレットキーから安全に読み込む
                api_key = st.secrets["GEMINI_API_KEY"]
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"福岡空港 {selected_spot_name}での空撮助言。時刻{sim_hour}時、風向{wind_dir}°、RWY{current_rwy}。マニアックな戦術を解説せよ。Markdown記号は禁止。"
                response = model.generate_content(prompt).text
                st.success(response)
            except Exception as e:
                st.error(f"🚨 エラー詳細: {e}")
