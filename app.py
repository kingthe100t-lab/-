import streamlit as st
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math
import numpy as np
from scipy.interpolate import interp1d
from google import genai
import pandas as pd

st.set_page_config(layout="wide", page_title="SKY-DIRECTOR PRO V2")
st.markdown("<h1 style='color: #0088ff;'>🛫 SKY-DIRECTOR PRO: 100 Spots Edition</h1>", unsafe_allow_html=True)

# 📂 100か所の極秘データベースを読み込み
@st.cache_data
def load_data():
    df = pd.read_csv("spots.csv")
    # ▼ 追加：緯度・経度の列にある「見えないゴミ」を強制的に破壊（NaN化）！
    df["緯度"] = pd.to_numeric(df["緯度"], errors="coerce")
    df["経度"] = pd.to_numeric(df["経度"], errors="coerce")
    # ゴミが破壊されて空っぽになった行を完全に消去
    df = df.dropna(subset=["緯度", "経度"])
    return df
try:
    df_spots = load_data()
except FileNotFoundError:
    st.error("🚨 エラー: GitHubに `spots.csv` がアップロードされていません！")
    st.stop()

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
st.markdown("### 🎯 ターゲット・フィルター")
filter_rwy = st.radio("運用滑走路でスポットを絞り込み", ["すべて", "16", "34"], horizontal=True)

if filter_rwy != "すべて":
    # 16/34 の両対応スポットも拾うための処理
    filtered_df = df_spots[df_spots['RWY'].str.contains(filter_rwy, na=False)]
else:
    filtered_df = df_spots

# 絞り込まれたリストからスポットを選択
selected_spot_name = st.selectbox("▼ ターゲット・スポット選択", filtered_df['スポット'].tolist())
spot_data = filtered_df[filtered_df['スポット'] == selected_spot_name].iloc[0]

col_map, col_tactical = st.columns([2, 1.2])

with col_map:
    # 全体マップの生成
    m = folium.Map(location=[33.580, 130.430], zoom_start=12, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    
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
        folium.CircleMarker([faf_pos[0], faf_pos[1]], radius=6, color="#00ff00", fill=True, tooltip="御笠川 ファイナル合流点").add_to(m)

  # 100スポットを地図上にプロット
    for idx, row in filtered_df.iterrows():
        is_selected = (row["スポット"] == selected_spot_name)
        color = "green" if is_selected else "red"
        # マップのピンにマウスを乗せると特徴が出る仕様！
        folium.Marker(
            [float(row["緯度"]), float(row["経度"])], # ← ココを書き換えました！
            tooltip=f"{row['No']}: {row['スポット']} ({row['特徴']})", 
            icon=folium.Icon(color=color, icon="camera", prefix="fa")
        ).add_to(m)

    st_folium(m, use_container_width=True, height=600)

with col_tactical:
    st.markdown(f"### 🌐 拡大サテライト: {spot_data['スポット']}")
    ms = folium.Map(location=[spot_data['緯度'], spot_data['経度']], zoom_start=18, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri", control_scale=True)
    folium.Marker([spot_data['緯度'], spot_data['経度']], icon=folium.Icon(color="green", icon="camera", prefix="fa")).add_to(ms)
    st_folium(ms, use_container_width=True, height=250)
    
    # マスターのデータをダッシュボードに表示！
    st.success(f"**📝 特徴:** {spot_data['特徴']}  \n**🕒 ベスト:** {spot_data['ベスト時間']}  \n**📷 焦点距離:** {spot_data['焦点距離']}")
    
    st.markdown("### 🤖 TACTICAL A.I.")
    if st.button("⚡ ブリーフィングをリクエスト", type="primary", use_container_width=True):
        with st.spinner("ANALYZING..."):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                client = genai.Client(api_key=api_key)
                
                # AIプロンプトにマスターのデータを注入！
                prompt = f"福岡空港の撮影スポット「{spot_data['スポット']}」での空撮助言。現在時刻は{sim_hour}時、風向{wind_dir}°、RWY{current_rwy}で運用中。この場所の特徴は「{spot_data['特徴']}」、マスターの持参する推奨焦点距離は「{spot_data['焦点距離']}」です。この機材と環境を活かしたマニアックな撮影戦術を解説せよ。Markdown記号は禁止。"
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                st.info(response.text)
            except Exception as e:
                st.error(f"🚨 エラー詳細: {e}")
