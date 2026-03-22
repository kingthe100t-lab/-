import streamlit as st
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math
import numpy as np
from scipy.interpolate import interp1d
from google import genai
import pandas as pd

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

# --- セッション状態の初期化（タッチ操作用） ---
if "selected_spot" not in st.session_state:
    st.session_state.selected_spot = df_spots.iloc[0]["スポット"]

# --- 気象・タイムライン・運用滑走路のシミュレート ---
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

# --- 🎯 ターゲット・フィルター機能 ---
filter_rwy = st.radio("🎯 運用滑走路でスポットを絞り込み", ["すべて", "16", "34"], horizontal=True)

if filter_rwy != "すべて":
    filtered_df = df_spots[df_spots['RWY'].str.contains(filter_rwy, na=False)]
else:
    filtered_df = df_spots

# もしフィルターで現在の選択スポットが消えたら、リストの一番上に切り替える
if filtered_df.empty or st.session_state.selected_spot not in filtered_df["スポット"].values:
    if not filtered_df.empty:
        st.session_state.selected_spot = filtered_df.iloc[0]["スポット"]
    else:
        st.error("🚨 選択された条件に合うスポットがありません。フィルターを解除してください。")
        st.stop()

spot_data = filtered_df[filtered_df['スポット'] == st.session_state.selected_spot].iloc[0]

# 操作案内を表示
st.info("👆 **地図上の赤いピンをタッチ（クリック）すると、そのスポットの戦術情報に切り替わります。**")

col_map, col_tactical = st.columns([2, 1.2])

with col_map:
    # 全体マップの生成
    airport_center = [33.585, 130.445] # 撮影ターゲット（被写体）の中心
    m = folium.Map(location=airport_center, zoom_start=13, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    
    rwy16_pos = np.array([33.5955, 130.4439])
    rwy34_pos = np.array([33.5715, 130.4553])
    
    def create_smooth_path(points, num_points=120):
        lats, lons = [p[0] for p in points], [p[1] for p in points]
        t = np.zeros(len(points))
        for i in range(1, len(points)):
            t[i] = t[i-1] + math.sqrt((lats[i]-lats[i-1])**2 + (lons[i]-lons[i-1])**2)
        t /= t[-1] 
        return [[float(lat), float(lon)] for lat, lon in zip(interp1d(t, lats, kind='cubic')(np.linspace(0, 1, num_points)), interp1d(t, lons, kind='cubic')(np.linspace(0, 1, num_points)))]

    # 進入ルート描写
    if current_rwy == "16":
        path_coords = create_smooth_path([[33.720, 130.340], [33.660, 130.390], [33.620, 130.425], [rwy16_pos[0], rwy16_pos[1]]], 50)
        AntPath(locations=path_coords, delay=800, weight=6, color="#00f0ff", pulse_color="#ffffff").add_to(m)
    else:
        rwy_vec = rwy16_pos - rwy34_pos
        faf_pos = rwy34_pos - rwy_vec * 1.8 
        curve_points = [
            [33.6800, 130.3000], [33.6200, 130.3500], [33.5700, 130.3950], 
            [33.5400, 130.4150], [33.5180, 130.4350], [33.5150, 130.4550], 
            [faf_pos[0], faf_pos[1]]
        ]
        path_coords = create_smooth_path(curve_points, 120) + [[faf_pos[0], faf_pos[1]], [rwy34_pos[0], rwy34_pos[1]]]
        AntPath(locations=path_coords, delay=800, weight=6, color="#0088ff", pulse_color="#ffffff").add_to(m)

    # ▼ 究極進化：太陽アイコンなしの光環境シミュレーター
    # 太陽の方位角を計算（北=0, 東=90, 南=180, 西=270）
    sun_azimuth = 180 + (sim_hour - 12) * 15
    sun_azimuth_rad = math.radians(sun_azimuth)

    # 1. 空の彼方から降り注ぐ「光の束（平行光線）」
    # 太陽アイコンを削除し、AntPathの始点を地図の外（非常に遠く）に設定
    r_sun_far = 0.15 # 中心からの距離（約15km、地図の外）
    sun_lat_far = airport_center[0] - r_sun_far * math.cos(sun_azimuth_rad)
    sun_lon_far = airport_center[1] - r_sun_far * math.sin(sun_azimuth_rad)
    
    AntPath(
        locations=[[sun_lat_far, sun_lon_far], airport_center],
        color="#FFD700",
        weight=20, # 太くして「束」にする
        opacity=0.4, # 半透明で洗練させる
        dash_array=[50, 100], # 長い点線で光線を表現
        delay=1500, # ゆっくり動かす
        pulse_color="#FFFFFF",
        tooltip=f"☀️ 太陽光の向き ({sim_hour}:00)"
    ).add_to(m)

    # 2. 被写体（飛行機）の配置（光の表現付きSVGアイコン）
    plane_angle = 160 if current_rwy == "16" else 340 # 運用RWYに合わせて機体の向きを変える
    
    # SVGによる洗練された飛行機アイコン（光の後光付き）
    # SVG全体を太陽の方位（sun_azimuth）で回転させ、光の向きを固定
    # その中で、飛行機文字を逆回転させて向きを調整
    plane_svg = f"""
    <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style="transform: rotate({sun_azimuth}deg); transform-origin: center;">
        <defs>
            <radialGradient id="sunlightGlow" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
                <stop offset="0%" style="stop-color:#FFD700;stop-opacity:0.7" />
                <stop offset="100%" style="stop-color:#FFD700;stop-opacity:0" />
            </radialGradient>
        </defs>
        <path d="M 50,50 L 30,0 A 50,50 0 0 1 70,0 Z" fill="url(#sunlightGlow)" transform="translate(0, -10)" />
        
        <text x="50" y="65" font-size="50" text-anchor="middle" style="transform: rotate({plane_angle - sun_azimuth}deg); transform-origin: 50px 50px; text-shadow: 2px 2px 5px #000;">✈️</text>
    </svg>
    """
    
    folium.Marker(
        airport_center,
        tooltip="被写体（アプローチ機）",
        icon=folium.DivIcon(
            icon_size=(100, 100),
            icon_anchor=(50, 50), # 中心を合わせる
            html=plane_svg
        )
    ).add_to(m)

    # 3. カメラの視線（現在選択しているスポットから被写体へ）
    spot_lat = float(spot_data['緯度'])
    spot_lon = float(spot_data['経度'])
    folium.PolyLine(
        locations=[[spot_lat, spot_lon], airport_center],
        color="#00FF00",
        weight=3,
        dash_array="
