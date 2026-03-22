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
if st.session_state.selected_spot not in filtered_df["スポット"].values:
    st.session_state.selected_spot = filtered_df.iloc[0]["スポット"]

spot_data = filtered_df[filtered_df['スポット'] == st.session_state.selected_spot].iloc[0]

# プルダウンを廃止し、操作案内を表示
st.info("👆 **地図上の赤いピンをタッチ（クリック）すると、そのスポットの戦術情報に切り替わります。**")

col_map, col_tactical = st.columns([2, 1.2])

with col_map:
    # 全体マップの生成
    m = folium.Map(location=[33.585, 130.445], zoom_start=12, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    
    airport_center = [33.585, 130.445] # 撮影ターゲット（被写体）の中心
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

    # ▼ 新規：ジオラマ光線シミュレーター
    # 1. 被写体（飛行機）の配置
    plane_angle = 160 if current_rwy == "16" else 340 # 運用RWYに合わせて機体の向きを変える
    plane_html = f'<div style="font-size: 35px; transform: rotate({plane_angle}deg); text-shadow: 2px 2px 5px #000;">✈️</div>'
    folium.Marker(
        airport_center,
        tooltip="被写体（アプローチ機）",
        icon=folium.DivIcon(html=plane_html, icon_anchor=(17, 17))
    ).add_to(m)

    # 2. 太陽の配置
    sun_azimuth = 90 + (sim_hour - 6) * 15 # 方位角 (6時=90度(東), 12時=180度(南), 18時=270度(西))
    sun_azimuth_rad = math.radians(sun_azimuth)
    r_sun = 0.05 # 中心からの距離
    sun_lat = airport_center[0] + r_sun * math.cos(sun_azimuth_rad)
    sun_lon = airport_center[1] + r_sun * math.sin(sun_azimuth_rad)
    
    folium.Marker(
        [sun_lat, sun_lon],
        tooltip=f"太陽 ({sim_hour}:00)",
        icon=folium.DivIcon(html='<div style="font-size: 35px; text-shadow: 0 0 15px #FFD700;">☀️</div>', icon_anchor=(17, 17))
    ).add_to(m)

    # 3. 太陽から被写体へ降り注ぐ「光の束（アニメーション）」
    AntPath(
        locations=[[sun_lat, sun_lon], airport_center],
        color="#FFD700",
        weight=8,
        opacity=0.6,
        dash_array=[10, 15],
        delay=1000,
        pulse_color="#FFFFFF",
        tooltip="太陽光の向き"
    ).add_to(m)

    # 4. カメラの視線（現在選択しているスポットから被写体へ）
    spot_lat = float(spot_data['緯度'])
    spot_lon = float(spot_data['経度'])
    folium.PolyLine(
        locations=[[spot_lat, spot_lon], airport_center],
        color="#00FF00",
        weight=3,
        dash_array="5, 8",
        tooltip="カメラの視線（アングル）"
    ).add_to(m)

    # 100スポットを地図上にプロット（タッチ対応）
    for idx, row in filtered_df.iterrows():
        is_selected = (row["スポット"] == st.session_state.selected_spot)
        color = "green" if is_selected else "red"
        folium.Marker(
            [float(row["緯度"]), float(row["経度"])], 
            tooltip=row['スポット'], # タッチで名前を取得するためにシンプル化
            icon=folium.Icon(color=color, icon="camera", prefix="fa")
        ).add_to(m)

    # ▼ ここで地図のタッチ（クリック）イベントを受け取る！
    map_data = st_folium(m, use_container_width=True, height=600, key="main_map")
    
    # ピンがタッチされたら、画面を再描画してスポットを切り替える
    if map_data and map_data.get("last_object_clicked_tooltip"):
        clicked_tooltip = map_data["last_object_clicked_tooltip"]
        if clicked_tooltip in filtered_df["スポット"].values:
            if clicked_tooltip != st.session_state.selected_spot:
                st.session_state.selected_spot = clicked_tooltip
                st.rerun() # 瞬時に画面を更新！

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
                prompt = f"福岡空港の撮影スポット「{spot_data['スポット']}」での空撮助言。現在時刻は{sim_hour}時、風向{wind_dir}°、RWY{current_rwy}で運用中。この場所の特徴は「{spot_data['特徴']}」、マスターの持参する推奨焦点距離は「{spot_data['焦点距離']}」です。この機材と環境を活かしたマニアックな撮影戦術を解説せよ。Markdown記号は禁止。"
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                st.info(response.text)
            except Exception as e:
                st.error(f"🚨 エラー詳細: {e}")
