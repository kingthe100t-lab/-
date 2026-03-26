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
import urllib.request
import json
from branca.element import Element

st.set_page_config(layout="wide", page_title="SKY-DIRECTOR PRO")

# ▼ AVIONICS_OS カスタムデザインCSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Manrope:wght@300;400;500;600;700&display=swap');

    .stApp {
        background-color: #0a0e1a !important;
        background-image: 
            radial-gradient(circle, rgba(167, 170, 187, 0.15) 1px, transparent 1px),
            linear-gradient(to bottom right, #0a0e1a, #0e1320, #0a0e1a) !important;
        background-size: 20px 20px, 100% 100% !important;
        font-family: 'Manrope', sans-serif !important;
        color: #e2e4f6 !important;
    }

    h1, h2, h3, h4, h5, h6, label, .st-emotion-cache-10trblm p {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #81ecff !important;
        letter-spacing: 0.05em;
    }

    h1 {
        text-shadow: 0 0 20px rgba(0,229,255,0.3);
        text-transform: uppercase;
        font-weight: 700 !important;
        font-size: 24px !important;
        margin-bottom: 20px !important;
    }

    div[data-testid="metric-container"], 
    .stRadio > div, 
    .stSlider > div {
        background: rgba(32, 37, 55, 0.4) !important;
        backdrop-filter: blur(20px) !important;
        border-top: 1px solid rgba(129, 236, 255, 0.15) !important;
        border-bottom: 1px solid rgba(129, 236, 255, 0.05) !important;
        border-radius: 8px !important;
        padding: 15px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3) !important;
    }

    div[data-testid="stMetricValue"] {
        color: #e2e4f6 !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }

    button[kind="primary"] {
        background: linear-gradient(to right, #81ecff, #00e3fd) !important;
        color: #004d57 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: bold !important;
        border: none !important;
        box-shadow: 0 0 15px rgba(129,236,255,0.3) !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        transition: transform 0.2s;
    }
    button[kind="primary"]:hover {
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# 🛫 タイトルとアイコン
title_icon_svg = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M21 16v-2l-8-5V3.5C13 2.67 12.33 2 11.5 2S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z" fill="#0088ff"/>
</svg>
"""

st.markdown(f"""
    <h1 style='color: #0088ff; font-weight: 900;'>
        <span style='vertical-align: middle; margin-right: 15px; font-size: 1.5em;'>{title_icon_svg}</span>
        SKY-DIRECTOR PRO
    </h1>
""", unsafe_allow_html=True)

# PROCEDURAL ADVISORY パネル
advisory_html = """
<div style="background: rgba(10, 14, 26, 0.6); backdrop-filter: blur(10px); border: 1px solid rgba(129, 236, 255, 0.3); border-radius: 6px; padding: 12px 16px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0, 227, 253, 0.1);">
    <div style="color: #81ecff; font-family: 'Space Grotesk', sans-serif; font-size: 10px; font-weight: 600; letter-spacing: 0.15em; margin-bottom: 8px; border-bottom: 1px solid rgba(129, 236, 255, 0.2); padding-bottom: 4px; display: inline-block;">
        PROCEDURAL ADVISORY
    </div>
    <div style="color: #a7aabb; font-family: 'Manrope', sans-serif; font-size: 13px; display: flex; align-items: center;">
        <span style="font-size: 16px; margin-right: 8px;">👆</span>
        【操作方法】地図上の「カメラピン」をタッチで撮影場所変更。道や空き地をタッチすると、そこに被写体（
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: text-bottom; margin: 0 4px;">
            <path d="M21 16v-2l-8-5V3.5C13 2.67 12.33 2 11.5 2S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z" fill="#81ecff"/>
        </svg>
        ）が瞬間移動します！
    </div>
</div>
"""
st.markdown(advisory_html, unsafe_allow_html=True)

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

if "selected_spot" not in st.session_state:
    st.session_state.selected_spot = df_spots.iloc[0]["スポット"]
if "plane_lat" not in st.session_state:
    st.session_state.plane_lat = 33.585
if "plane_lon" not in st.session_state:
    st.session_state.plane_lon = 130.445
if "processed_click" not in st.session_state:
    st.session_state.processed_click = None

metrics_placeholder = st.empty()
st.markdown("---")

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

col_map, col_tactical = st.columns([2, 1.2])

with col_map:
    st.markdown("##### ⚙️ シミュレーション・コントロール")
    col_s1, col_s2 = st.columns([1, 1.5])
    
    with col_s1:
        sim_day = st.radio("📅 予定日", ["本日", "明日"], horizontal=True)
    with col_s2:
        sim_hour = st.slider("☀️ タイムライン（時刻）", 7, 22, 12)

    @st.cache_data(ttl=3600)
    def get_weather_forecast():
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=33.585&longitude=130.445&hourly=winddirection_10m,windspeed_10m&timezone=Asia%2FTokyo"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as res:
                return json.loads(res.read())
        except:
            return None

    weather_data = get_weather_forecast()

    if weather_data:
        jst = datetime.timezone(datetime.timedelta(hours=9))
        target_date = datetime.datetime.now(jst)
        if sim_day == "明日":
            target_date += datetime.timedelta(days=1)
            
        target_time_str = f"{target_date.strftime('%Y-%m-%d')}T{sim_hour:02d}:00"
        
        try:
            idx = weather_data['hourly']['time'].index(target_time_str)
            wind_dir = weather_data['hourly']['winddirection_10m'][idx]
            wind_speed_kmh = weather_data['hourly']['windspeed_10m'][idx]
            wind_speed = int(wind_speed_kmh * 0.539957) 

            if 90 <= wind_dir <= 270:
                current_rwy = "16"
            else:
                current_rwy = "34"
        except:
            wind_dir, wind_speed, current_rwy = 160, 6, "16" 
    else:
        wind_dir, wind_speed, current_rwy = 160, 6, "16" 

    plane_heading = 156 if current_rwy == "16" else 336

    with metrics_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("風向", f"{wind_dir}°")
        c2.metric("風速", f"{wind_speed} kt")
        c3.metric("運用滑走路", f"RWY {current_rwy}")
        c4.metric("予定日時", f"{sim_day} {sim_hour}:00")

    m = folium.Map(location=[33.560, 130.460], zoom_start=12, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    
    # ▼ 追加：ズームと位置をブラウザ側に記憶させ、チカチカせずに縮尺を維持する魔法のスクリプト
    keep_zoom_js = """
    <script>
    setTimeout(function(){
        var map_instance = null;
        for (var key in window) {
            if (key.startsWith("map_") && window[key].getZoom) {
                map_instance = window[key];
                break;
            }
        }
        if (map_instance) {
            var savedZoom = sessionStorage.getItem('sd_map_zoom');
            var savedLat = sessionStorage.getItem('sd_map_lat');
            var savedLng = sessionStorage.getItem('sd_map_lng');
            if (savedZoom !== null && savedLat !== null && savedLng !== null) {
                map_instance.setView([parseFloat(savedLat), parseFloat(savedLng)], parseInt(savedZoom), {animate: false});
            }
            map_instance.on('moveend', function() {
                sessionStorage.setItem('sd_map_zoom', map_instance.getZoom());
                var center = map_instance.getCenter();
                sessionStorage.setItem('sd_map_lat', center.lat);
                sessionStorage.setItem('sd_map_lng', center.lng);
            });
        }
    }, 200);
    </script>
    """
    m.get_root().html.add_child(Element(keep_zoom_js))
    
    wind_html = f'<div style="font-size: 35px; color: #81ecff; text-shadow: 2px 2px 4px #000; transform: rotate({wind_dir}deg); transform-origin: center;">⬇</div>'
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
        AntPath(locations=path_coords, delay=800, weight=6, color="#81ecff", pulse_color="#ffffff", tooltip="RWY16 アプローチ・ルート").add_to(m)
    else:
        faf_pos = [33.550558624462184, 130.47508525096282]
        curve_points = [
            [33.6800, 130.3000], [33.6200, 130.3500], [33.5700, 130.3950], 
            [33.5400, 130.4150], [33.5180, 130.4400], [33.5250, 130.4650], 
            faf_pos
        ]
        path_coords = create_smooth_path(curve_points, 120) + [faf_pos, [rwy34_pos[0], rwy34_pos[1]]]
        AntPath(locations=path_coords, delay=800, weight=6, color="#00e3fd", pulse_color="#ffffff", tooltip="RWY34 アプローチ・ルート").add_to(m)
        folium.CircleMarker(faf_pos, radius=6, color="#00ff00", fill=True, tooltip="ファイナル合流点").add_to(m)

    sun_azimuth = 180 + (sim_hour - 12) * 15
    sun_azimuth_rad = math.radians(sun_azimuth)
    
    x1 = 50 + 50 * math.sin(sun_azimuth_rad)
    y1 = 50 - 50 * math.cos(sun_azimuth_rad)
    x2 = 50 - 50 * math.sin(sun_azimuth_rad)
    y2 = 50 + 50 * math.cos(sun_azimuth_rad)

    plane_rot = plane_heading 
    plane_pos = [st.session_state.plane_lat, st.session_state.plane_lon]

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
                <stop offset="100%" stop-color="#FF9900" stop-opacity="0.0" />
            </linearGradient>
        </defs>
        <rect width="100" height="100" fill="url(#sunLight)" style="pointer-events: none !important;" />
        
        <svg x="49" y="49" width="2" height="2" viewBox="0 0 24 24" style="pointer-events: none !important;">
            <g style="transform: rotate({plane_rot}deg); transform-origin: 12px 12px; pointer-events: none !important;">
                <path d="M21,16v-2l-8-5V3.5C13,2.67,12.33,2,11.5,2S10,2.67,10,3.5V9l-8,5v2l8-2.5V19l-2,1.5V22l3.5-1l3.5,1v-1.5L13,19v-5.5L21,16z" 
                      fill="#222222" stroke="none" stroke-width="0" stroke-linejoin="round"
                      style="pointer-events: none !important;"/>
            </g>
        </svg>
    </svg>
    """
    
    folium.Marker(
        plane_pos,
        icon=folium.DivIcon(
            icon_size=(4000, 4000), 
            icon_anchor=(2000, 2000), 
            html=plane_svg,
            class_name="ghost-marker" 
        ),
        interactive=False 
    ).add_to(m)

    spot_lat = float(spot_data['緯度'])
    spot_lon = float(spot_data['経度'])
    
    folium.PolyLine(
        locations=[[spot_lat, spot_lon], plane_pos],
        color="#81ecff",
        weight=3,
        dash_array="5, 8",
        tooltip="カメラの視線（アングル）"
    ).add_to(m)

    def get_camera_svg(is_selected):
        bg_color = "#81ecff" if is_selected else "#444756"
        return f"""
        <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(1px 2px 3px rgba(0,0,0,0.5));">
            <circle cx="12" cy="12" r="11" fill="{bg_color}" stroke="#0a0e1a" stroke-width="2"/>
            <path d="M 8 10 L 9.5 8.5 L 14.5 8.5 L 16 10 L 17 10 A 1 1 0 0 1 18 11 L 18 16 A 1 1 0 0 1 17 17 L 7 17 A 1 1 0 0 1 6 16 L 6 11 A 1 1 0 0 1 7 10 Z" fill="#0a0e1a"/>
            <circle cx="12" cy="13.5" r="2.5" fill="{bg_color}"/>
        </svg>
        """

    for idx, row in filtered_df.iterrows():
        is_selected = (row["スポット"] == st.session_state.selected_spot)
        folium.Marker(
            [float(row["緯度"]), float(row["経度"])], 
            tooltip=row['スポット'], 
            icon=folium.DivIcon(
                html=get_camera_svg(is_selected),
                icon_size=(24, 24),
                icon_anchor=(12, 12)
            )
        ).add_to(m)

    # ▼ 修正：ズームと座標の監視を外し、チカチカするリロードを完全に遮断
    map_data = st_folium(
        m, 
        use_container_width=True, 
        height=600, 
        key="main_map",
        returned_objects=["last_object_clicked_tooltip", "last_clicked"]
    )
    
    if map_data:
        clicked_tooltip = map_data.get("last_object_clicked_tooltip")
        if clicked_tooltip and clicked_tooltip in filtered_df["スポット"].values:
            if clicked_tooltip != st.session_state.selected_spot:
                st.session_state.selected_spot = clicked_tooltip
                st.rerun() 
        
        clicked_bg = map_data.get("last_clicked")
        if clicked_bg and clicked_bg != st.session_state.processed_click:
            st.session_state.processed_click = clicked_bg
            st.session_state.plane_lat = clicked_bg["lat"]
            st.session_state.plane_lon = clicked_bg["lng"]
            st.rerun()

with col_tactical:
    st.markdown(f"### 🌐 選択中: {spot_data['スポット']}")
    ms = folium.Map(location=[spot_lat, spot_lon], zoom_start=18, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri", control_scale=True)
    
    folium.Marker(
        [spot_lat, spot_lon], 
        icon=folium.DivIcon(html=get_camera_svg(True), icon_size=(24, 24), icon_anchor=(12, 12))
    ).add_to(ms)
    
    st_folium(
        ms, 
        use_container_width=True, 
        height=250, 
        key="sub_map",
        returned_objects=[]
    )
    
    st.success(f"**📝 特徴:** {spot_data['特徴']}  \n**🕒 ベスト:** {spot_data['ベスト時間']}  \n**📷 焦点距離:** {spot_data['焦点距離']}")
    
    st.markdown("### 🤖 TACTICAL A.I.")
    if st.button("⚡ ブリーフィングをリクエスト", type="primary", use_container_width=True):
        with st.spinner("ANALYZING..."):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                client = genai.Client(api_key=api_key)
                prompt = f"福岡空港の撮影スポット「{spot_data['スポット']}」での空撮助言。シミュレーション予定日時は「{sim_day}の{sim_hour}時」、風向は{wind_dir}度で風速は{wind_speed}kt。被写体の飛行機はRWY{current_rwy}運用に従い機首を{plane_heading}度に向けています。この場所の特徴は「{spot_data['特徴']}」、マスターの持参する推奨焦点距離は「{spot_data['焦点距離']}」です。この機材と環境を活かしたマニアックな撮影戦術を解説せよ。Markdown記号は禁止。"
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                st.info(response.text)
            except Exception as e:
                st.error(f"🚨 エラー詳細: {e}")
