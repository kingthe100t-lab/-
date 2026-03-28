import streamlit as st
import pandas as pd
import json
import math
import numpy as np
from scipy.interpolate import interp1d

# --- ⚙️ ページ基本設定 ---
st.set_page_config(layout="wide", page_title="SKY-DIRECTOR PRO", initial_sidebar_state="collapsed")

# ▼ iOSのスクロールバグ対策 & フルスクリーン対応
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding: 0px !important; max-width: 100% !important;}
        iframe {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            border: none !important;
            z-index: 99999 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 📦 データ読み込み ---
@st.cache_data
def load_data():
    df = pd.read_csv("spots.csv")
    df["緯度"] = pd.to_numeric(df["緯度"], errors="coerce")
    df["経度"] = pd.to_numeric(df["経度"], errors="coerce")
    return df.dropna(subset=["緯度", "経度"])

df_spots = load_data()
api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- ✈️ 軌跡計算 (Cubicスプライン) ---
rwy16_pos = [33.5955, 130.4439]
rwy34_pos = [33.5750, 130.4581]

def create_smooth_path(points, num_points=120):
    lats, lons = [p[0] for p in points], [p[1] for p in points]
    t = np.zeros(len(points))
    for i in range(1, len(points)):
        t[i] = t[i-1] + math.sqrt((lats[i]-lats[i-1])**2 + (lons[i]-lons[i-1])**2)
    if t[-1] == 0: return [[float(lat), float(lon)] for lat, lon in zip(lats, lons)]
    t /= t[-1] 
    return [[float(lat), float(lon)] for lat, lon in zip(interp1d(t, lats, kind='cubic')(np.linspace(0, 1, num_points)), interp1d(t, lons, kind='cubic')(np.linspace(0, 1, num_points)))]

# 🛬 アプローチ (Arrival)
path_16 = create_smooth_path([[33.720, 130.340], [33.660, 130.390], [33.620, 130.425], rwy16_pos], 50)
faf_pos = [33.550558624462184, 130.47508525096282]
path_34 = create_smooth_path([[33.6800, 130.3000], [33.6200, 130.3500], [33.5700, 130.3950], [33.5400, 130.4150], [33.5180, 130.4400], [33.5250, 130.4650], faf_pos], 120) + [faf_pos, rwy34_pos]

# 🛫 離陸 (Departure: マスター指定の3点に中継点を足して4点確保)
dep_path_16 = create_smooth_path([rwy34_pos, [33.579172885448706, 130.45531520290436], [33.56430, 130.46693], [33.54943579810327, 130.47855674420796]], 60)
dep_path_34 = create_smooth_path([rwy16_pos, [33.59444398997148, 130.44502712636253], [33.61313, 130.43086], [33.63183125340424, 130.41670130435546]], 60)

# --- 🌐 フロントエンド構築 ---
html_app = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/leaflet-ant-path@1.3.0/dist/leaflet-ant-path.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700&family=Manrope:wght@400;700&display=swap" rel="stylesheet">
    <style>
        html, body {{ background: #04060d; color: #e2e4f6; font-family: 'Manrope', sans-serif; margin: 0; padding: 0; height: 100%; overflow: hidden; position: fixed; width: 100%; }}
        .app-container {{ position: absolute; inset: 0; overflow-y: auto; -webkit-overflow-scrolling: touch; padding: 1.5rem; background: radial-gradient(circle at center, #0a0e1a 0%, #020308 100%); }}
        .glass-panel {{ background: rgba(15, 20, 35, 0.6); backdrop-filter: blur(20px); border: 1px solid rgba(129, 236, 255, 0.2); border-radius: 12px; }}
        .neon-text {{ color: #81ecff; text-shadow: 0 0 15px rgba(129,236,255,0.6); font-family: 'Space Grotesk', sans-serif; }}
        .cyber-btn {{ background: linear-gradient(90deg, #81ecff, #00e3fd); color: #004d57; font-weight: 700; border-radius: 6px; }}
        
        /* 地図の白枠対策 */
        .leaflet-container {{ background: #0a0e1a !important; outline: none !important; }}
        .leaflet-container * {{ outline: none !important; -webkit-tap-highlight-color: transparent !important; }}
        
        input[type=range] {{ -webkit-appearance: none; background: rgba(129,236,255,0.2); height: 4px; border-radius: 2px; width: 100%; }}
        input[type=range]::-webkit-slider-thumb {{ -webkit-appearance: none; height: 18px; width: 18px; border-radius: 50%; background: #81ecff; box-shadow: 0 0 10px #81ecff; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="app-container">
        <div class="max-w-[1400px] mx-auto flex flex-col gap-6 w-full">
            <h1 class="text-3xl font-black flex items-center gap-4 neon-text uppercase">
                <svg width="32" height="32" viewBox="0 0 24 24" style="filter: drop-shadow(0 0 8px #81ecff);"><path d="M21 16v-2l-8-5V3.5C13 2.67 12.33 2 11.5 2S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z" fill="#81ecff"/></svg>
                SKY-DIRECTOR PRO
            </h1>

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div class="lg:col-span-7 flex flex-col gap-4">
                    <div class="grid grid-cols
