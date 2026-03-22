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

# --- セッション状態の初期化 ---
if "selected_spot" not in st.session_state:
    st.session_state.selected_spot = df_spots.iloc[0]["スポット"]
# ▼ 新規：飛行機の位置と向きを記憶するシステム
if "plane_lat" not in st.session_state:
    st.session_state.plane_lat = 33.585
if "plane_lon" not in st.session_state:
    st.session_state.plane_lon = 130.445
if "plane_heading" not in st.session_state:
    st.session_state.plane_heading = 160
if "processed_click" not in st.session_state:
    st.session_state.processed_click = None

# --- コントロールパネル ---
col_time, col_plane = st.columns([1, 1])
with col_time:
    sim_hour = st.slider("☀️ タイムライン（太陽の位置）", 7, 22, 12)
with col_plane:
    # ▼ 新規：機首の向きを360度自由に変えられるスライダー
    st.session_state.plane_heading = st.slider("✈️ 飛行機の向き（機首角）", 0, 359, st.session_state.plane_heading)

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

# 操作案内
st.info("👆 **【操作方法】** 地図上の「赤いピン」をタッチで撮影場所変更。**道や空き地をタッチすると、そこに飛行機（✈️）が瞬間移動します！**")

col_map, col_tactical = st.columns([2, 1.2])

with col_map:
    # 全体マップの生成
    m = folium.Map(location=[33.585, 130.445], zoom_start=13, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    
    # 太陽の方位角を計算
    sun_azimuth = 180 + (sim_hour - 12) * 15
    sun_azimuth_rad = math.radians(sun_azimuth)

    # 現在の被写体（飛行機）の座標
    plane_pos = [st.session_state.plane_lat, st.session_state.plane_lon]

    # 1. 空の彼方から飛行機へ降り注ぐ「光の束」
    r_sun_far = 0.15 
    sun_lat_far = plane_pos[0] - r_sun_far * math.cos(sun_azimuth_rad)
    sun_lon_far = plane_pos[1] - r_sun_far * math.sin(sun_azimuth_rad)
    
    AntPath(
        locations=[[sun_lat_far, sun_lon_far], plane_pos],
        color="#FFD700",
        weight=20, 
        opacity=0.4, 
        dash_array="50, 100", 
        delay=1500, 
        pulse_color="#FFFFFF",
        tooltip="太陽光の向き"
    ).add_to(m)

    # 2. 被写体（飛行機）の配置
    plane_angle = st.session_state.plane_heading
    
    plane_svg = f"""
    <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style="transform: rotate({sun_azimuth}deg); transform-origin: center;">
        <defs>
            <radialGradient id="sunlightGlow" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
                <stop offset="0%" style="stop-color:#FFD700;stop-opacity:0.8" />
                <stop offset="100%" style="stop-color:#FFD700;stop-opacity:0" />
            </radialGradient>
        </defs>
        <path d="M 50,50 L 30,0 A 50,50 0 0 1 70,0 Z" fill="url(#sunlightGlow)" transform="translate(0, -10)" />
        <text x="50" y="65" font-size="50" text-anchor="middle" style="transform: rotate({plane_angle - sun_azimuth}deg); transform-origin: 50px 50px; text-shadow: 2px 2px 8px #000;">✈️</text>
    </svg>
    """
    
    folium.Marker(
        plane_pos,
        tooltip="ターゲット被写体（タッチで移動可能）",
        icon=folium.DivIcon(
            icon_size=(100, 100),
            icon_anchor=(50, 50), 
            html=plane_svg
        )
    ).add_to(m)

    # 3. カメラの視線（現在選択しているスポットから飛行機へ）
    spot_lat = float(spot_data['緯度'])
    spot_lon = float(spot_data['経度'])
    
    folium.PolyLine(
        locations=[[spot_lat, spot_lon], plane_pos],
        color="#00FF00",
        weight=3,
        dash_array="5, 8",
        tooltip="カメラの視線（アングル）"
    ).add_to(m)

    # 100スポットを地図上にプロット
    for idx, row in filtered_df.iterrows():
        is_selected = (row["スポット"] == st.session_state.selected_spot)
        color = "green" if is_selected else "red"
        folium.Marker(
            [float(row["緯度"]), float(row["経度"])], 
            tooltip=row['スポット'], 
            icon=folium.Icon(color=color, icon="camera", prefix="fa")
        ).add_to(m)

    # ▼ マップのイベントを監視
    map_data = st_folium(m, use_container_width=True, height=600, key="main_map")
    
    if map_data:
        # ピンがクリックされた場合（スポット変更）
        clicked_tooltip = map_data.get("last_object_clicked_tooltip")
        if clicked_tooltip and clicked_tooltip in filtered_df["スポット"].values:
            if clicked_tooltip != st.session_state.selected_spot:
                st.session_state.selected_spot = clicked_tooltip
                st.rerun() 
        
        # ▼ 新規：ピン以外の「地図上の場所」がクリックされた場合（飛行機の移動）
        clicked_bg = map_data.get("last_clicked")
        if clicked_bg and clicked_bg != st.session_state.processed_click:
            # クリックした座標を記憶して飛行機をワープさせる
            st.session_state.processed_click = clicked_bg
            st.session_state.plane_lat = clicked_bg["lat"]
            st.session_state.plane_lon = clicked_bg["lng"]
            st.rerun()

with col_tactical:
    st.markdown(f"### 🌐 選択中: {spot_data['スポット']}")
    ms = folium.Map(location=[spot_lat, spot_lon], zoom_start=18, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri", control_scale=True)
    folium.Marker([spot_lat, spot_lon], icon=folium.Icon(color="green", icon="camera", prefix="fa")).add_to(ms)
    st_folium(ms, use_container_width=True, height=250, key="sub_map")
    
    st.success(f"**📝 特徴:** {spot_data['特徴']}  \n**🕒 ベスト:** {spot_data['ベスト時間']}  \n**📷 焦点距離:** {spot_data['焦点距離']}")
    
    st.markdown("### 🤖 TACTICAL A.I.")
    if st.button("⚡ ブリーフィングをリクエスト", type="primary", use_container_width=True):
        with st.spinner("ANALYZING..."):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                client = genai.Client(api_key=api_key)
                prompt = f"福岡空港の撮影スポット「{spot_data['スポット']}」での空撮助言。現在時刻は{sim_hour}時。被写体の飛行機は現在地から見て機首を{st.session_state.plane_heading}度に向けています。この場所の特徴は「{spot_data['特徴']}」、マスターの持参する推奨焦点距離は「{spot_data['焦点距離']}」です。この機材と環境を活かしたマニアックな撮影戦術を解説せよ。Markdown記号は禁止。"
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                st.info(response.text)
            except Exception as e:
                st.error(f"🚨 エラー詳細: {e}")
