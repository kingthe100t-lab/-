import streamlit as st
import pandas as pd
import json
import math
import numpy as np
from scipy.interpolate import interp1d

# --- ⚙️ ページ基本設定 ---
st.set_page_config(layout="wide", page_title="SKY-DIRECTOR PRO", initial_sidebar_state="collapsed")

# ▼ 魔法の呪文：Streamlit特有の余白やメニューを「完全に消去」し、純粋なWebキャンバス化する
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding: 0px !important; max-width: 100% !important;}
        
        /* iframeを画面サイズに強制的に完全固定（iOSのハミ出しバグを防止） */
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

# --- 📦 データとAPIキーの読み込み ---
@st.cache_data
def load_data():
    df = pd.read_csv("spots.csv")
    df["緯度"] = pd.to_numeric(df["緯度"], errors="coerce")
    df["経度"] = pd.to_numeric(df["経度"], errors="coerce")
    return df.dropna(subset=["緯度", "経度"])

try:
    df_spots = load_data()
except FileNotFoundError:
    st.error("🚨 エラー: GitHubに `spots.csv` が見つかりません！")
    st.stop()
    
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = ""

# --- ✈️ アプローチ軌跡の事前計算（Pythonで計算してJSに渡す） ---
rwy16_pos = np.array([33.5955, 130.4439])
rwy34_pos = np.array([33.5750, 130.4581])

def create_smooth_path(points, num_points=120):
    lats, lons = [p[0] for p in points], [p[1] for p in points]
    t = np.zeros(len(points))
    for i in range(1, len(points)):
        t[i] = t[i-1] + math.sqrt((lats[i]-lats[i-1])**2 + (lons[i]-lons[i-1])**2)
    if t[-1] == 0: return [[float(lat), float(lon)] for lat, lon in zip(lats, lons)]
    t /= t[-1] 
    return [[float(lat), float(lon)] for lat, lon in zip(interp1d(t, lats, kind='cubic')(np.linspace(0, 1, num_points)), interp1d(t, lons, kind='cubic')(np.linspace(0, 1, num_points)))]

path_16 = create_smooth_path([[33.720, 130.340], [33.660, 130.390], [33.620, 130.425], [rwy16_pos[0], rwy16_pos[1]]], 50)
faf_pos = [33.550558624462184, 130.47508525096282]
curve_points = [
    [33.6800, 130.3000], [33.6200, 130.3500], [33.5700, 130.3950], 
    [33.5400, 130.4150], [33.5180, 130.4400], [33.5250, 130.4650], 
    faf_pos
]
path_34 = create_smooth_path(curve_points, 120) + [faf_pos, [rwy34_pos[0], rwy34_pos[1]]]
# 🛫 離陸（ディパーチャー）ルート
dep_curve_16 = [
    [rwy34_pos[0], rwy34_pos[1]], # RWY16離陸（南へ向かって飛ぶ）
    [33.57113402404754, 130.46083622611403], 
    [33.56545248920149, 130.46517714220687], # ←追加：2点目と3点目の「ど真ん中」の座標
    [33.55377778149313, 130.47464395170465]
]
dep_path_16 = create_smooth_path(dep_curve_16, 60)

dep_curve_34 = [
    [rwy16_pos[0], rwy16_pos[1]], # RWY34離陸（北へ向かって海へ抜ける）
    [33.60349227065672, 130.4388795538824],
    [33.61236625832645, 130.43230726779566],    # ←追加：2点目と3点目の「ど真ん中」の座標
    [33.63068902679922, 130.41857964050828]
]
dep_path_34 = create_smooth_path(dep_curve_34, 60)

# --- 🌐 超・本格的フロントエンド（HTML/JS/CSS）の構築 ---
html_app = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#04060d">
    <meta name="apple-mobile-web-app-title" content="SKY-DIRECTOR">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/leaflet-ant-path@1.3.0/dist/leaflet-ant-path.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Manrope:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
        /* 🌌 全体の文字にうっすらとした光のにじみ（70%にトーンダウン） */
        /* 🌌 iOSスクロールバグ対策：htmlとbodyのスクロールを完全に殺す */
        html, body {{ 
            background-color: #04060d; 
            color: #e2e4f6; 
            font-family: 'Manrope', sans-serif; 
            margin: 0; 
            padding: 0; 
            text-shadow: 0 0 11px rgba(167, 170, 187, 0.4); 
            height: 100%; 
            width: 100%;
            overflow: hidden; 
            position: fixed;
        }}

        /* 🌌 スクロールを許可する大元コンテナ（ここで全て滑らかに動かす） */
        .app-container {{
            background-image: 
                radial-gradient(circle, rgba(129, 236, 255, 0.9) 0.4px, transparent 1px),
                radial-gradient(circle, rgba(129, 236, 255, 0.2) 1px, transparent 6px),
                linear-gradient(to bottom right, #020308, #0a0e1a, #020308); 
            background-size: 35px 35px, 35px 35px, 100% 100%;
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            overflow-y: auto; 
            -webkit-overflow-scrolling: touch; /* 魔法の滑らかスクロール */
            padding: 1.5rem;
            box-sizing: border-box;
        }}
        .glass-panel {{
            background: rgba(15, 20, 35, 0.5); 
            backdrop-filter: blur(20px);
            border-top: 1px solid rgba(129, 236, 255, 0.3);
            border-bottom: 1px solid rgba(129, 236, 255, 0.1);
            border-radius: 8px;
            box-shadow: 0 8px 22px rgba(0, 229, 255, 0.15); /* パネルのグローを70%に */
        }}
        
        /* 🌌 見出しや専用フォントのネオングロー（70%にトーンダウン） */
        .neon-text {{ 
            text-shadow: 0 0 42px rgba(0,229,255,0.55), 0 0 42px rgba(0,229,255,0.35); 
            font-family: 'Space Grotesk', sans-serif; 
            color: #81ecff; 
        }}
        .space-font {{ 
            font-family: 'Space Grotesk', sans-serif; 
            text-shadow: 0 0 14px rgba(129, 236, 255, 0.55); 
        }}
        
        /* 🌌 ボタンやスライダーの光（70%にトーンダウン） */
        .cyber-btn {{
            background: linear-gradient(to right, #81ecff, #00e3fd); color: #004d57; font-family: 'Space Grotesk', sans-serif; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.1em; border: none; 
            box-shadow: 0 0 56px rgba(129,236,255,0.5); 
            cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;
        }}
        .cyber-btn:hover {{ 
            transform: scale(1.02); 
            box-shadow: 0 0 56px rgba(129,236,255,0.7); 
        }}
        
        input[type=range] {{ -webkit-appearance: none; background: transparent; width: 100%; outline: none; }}
        input[type=range]::-webkit-slider-thumb {{
            -webkit-appearance: none; height: 16px; width: 16px; border-radius: 50%; background: #81ecff; cursor: pointer; 
            box-shadow: 0 0 21px #81ecff; 
            margin-top: -6px;
        }}
        input[type=range]::-webkit-slider-runnable-track {{
            width: 100%; height: 4px; cursor: pointer; background: rgba(129, 236, 255, 0.2); border-radius: 2px;
            box-shadow: 0 0 7px rgba(129, 236, 255, 0.2); 
        }}
        .leaflet-container {{ background: #0a0e1a; font-family: 'Manrope', sans-serif; z-index: 1; outline: none !important; -webkit-tap-highlight-color: transparent !important; }}
        /* ▼ 追加：地図の中にある「すべて」の要素のフォーカス枠とタップ色を強制無効化 */
        .leaflet-container * {{ outline: none !important; -webkit-tap-highlight-color: transparent !important; }}
        .ghost-marker {{ pointer-events: none !important; background: transparent !important; border: none !important; margin-left: -12px !important; margin-top: -12px !important; }}
        .custom-radio input[type="radio"] {{ accent-color: #81ecff; cursor: pointer; filter: drop-shadow(0 0 7px #81ecff); }} 
    </style>
</head>
<body>
    <div class="app-container">
    <div class="max-w-[1400px] mx-auto flex flex-col gap-6 w-full">
        <h1 class="text-3xl font-black flex items-center gap-4 neon-text uppercase m-0">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 0 10px rgba(0, 229, 255, 0.6)) drop-shadow(0 0 20px rgba(0, 229, 255, 0.4));">
  <path d="M21 16v-2l-8-5V3.5C13 2.67 12.33 2 11.5 2S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z" fill="#81ecff"/>
</svg>
            SKY-DIRECTOR PRO
        </h1>
        
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
            <div class="lg:col-span-7 flex flex-col gap-4">
                <div class="flex flex-col md:flex-row gap-4">
                    <div class="glass-panel p-4 flex gap-4 text-sm items-center custom-radio flex-1">
                        <span class="text-[#81ecff] font-bold space-font tracking-widest">🎯 RWY FILTER</span>
                        <label class="flex items-center gap-1"><input type="radio" name="rwy" value="すべて" checked onchange="changeFilter(this.value)"> すべて</label>
                        <label class="flex items-center gap-1"><input type="radio" name="rwy" value="16" onchange="changeFilter(this.value)"> 16</label>
                        <label class="flex items-center gap-1"><input type="radio" name="rwy" value="34" onchange="changeFilter(this.value)"> 34</label>
                    </div>
                    <div class="glass-panel p-4 flex gap-6 text-sm flex-1">
                        <div class="custom-radio">
                            <span class="text-[#81ecff] font-bold block mb-2 space-font tracking-widest">📅 予定日</span>
                            <div class="flex gap-4">
                                <label class="flex items-center gap-1"><input type="radio" name="day" value="本日" checked onchange="changeDay(this.value)"> 本日</label>
                                <label class="flex items-center gap-1"><input type="radio" name="day" value="明日" onchange="changeDay(this.value)"> 明日</label>
                            </div>
                        </div>
                        <div class="flex-1 pr-2">
                            <span class="text-[#81ecff] font-bold block mb-2 space-font tracking-widest flex justify-between">
                                <span>☀️ タイムライン</span>
                                <span id="hourVal" class="text-white">12:00</span>
                            </span>
                            <input type="range" min="7" max="22" value="12" oninput="changeHourLive(this.value)" onchange="changeHour(this.value)">
                        </div>
                    </div>
                </div>

                <div class="glass-panel p-4 grid grid-cols-4 gap-2 text-center text-xs space-font tracking-widest">
                    <div><div class="text-[#a7aabb] mb-1">風向</div><div class="text-xl text-white font-bold" id="wDir">--</div></div>
                    <div><div class="text-[#a7aabb] mb-1">風速</div><div class="text-xl text-white font-bold" id="wSpd">--</div></div>
                    <div><div class="text-[#a7aabb] mb-1">運用滑走路</div><div class="text-[#00e3fd] text-xl font-bold" id="cRwy">--</div></div>
                    <div><div class="text-[#a7aabb] mb-1">予定日時</div><div class="text-xl text-white font-bold" id="cTime">--</div></div>
                </div>

                <div class="relative w-full h-[350px] lg:h-[600px]">
                        <div id="map" class="absolute inset-0 rounded-lg border border-[#81ecff]/30 shadow-[0_0_20px_rgba(0,229,255,0.1)]"></div>
                        <div id="wind-hud" class="absolute bottom-6 left-6 z-[400] pointer-events-none"></div>
                </div>
            </div>

            <div class="lg:col-span-5 flex flex-col gap-4">
                <div class="glass-panel p-5 border-l-4 border-l-[#81ecff]">
                    <div class="text-[#81ecff] space-font tracking-widest text-[10px] mb-1 uppercase">Selected Spot</div>
                    <h3 class="text-2xl font-bold text-white mb-4 space-font" id="spotName">--</h3>
                    <div class="text-sm text-[#e2e4f6] space-y-3">
                        <div><strong class="text-[#a7aabb] space-font tracking-widest block text-xs mb-1">📝 特徴</strong> <span id="spotDesc" class="leading-relaxed">--</span></div>
                        <div class="grid grid-cols-2 gap-2 mt-4">
                            <div><strong class="text-[#a7aabb] space-font tracking-widest block text-xs mb-1">🕒 ベスト時間</strong> <span id="spotTime">--</span></div>
                            <div><strong class="text-[#a7aabb] space-font tracking-widest block text-xs mb-1">📷 焦点距離</strong> <span id="spotLens">--</span></div>
                        </div>
                    </div>
                </div>

                <div class="glass-panel p-5 flex flex-col gap-4 flex-1">
                    <h3 class="text-[#81ecff] font-bold text-lg flex items-center gap-2 space-font tracking-widest">🤖 TACTICAL A.I.</h3>
                    <button class="cyber-btn w-full py-3 rounded" onclick="requestBriefing()">⚡ ブリーフィングをリクエスト</button>
                    <div id="ai-briefing" class="text-sm text-[#e2e4f6] p-4 bg-[#0a0e1a]/80 rounded border border-[#81ecff]/20 flex-1 overflow-y-auto whitespace-pre-wrap leading-relaxed min-h-[300px]">システム・スタンバイ...</div>
                </div>
            </div>
        </div>
    </div>
</div>
    <script>
        // Data injected from Python Server
        const spots = {df_spots.to_json(orient="records")};
        const path16 = {json.dumps(path_16)};
        const path34 = {json.dumps(path_34)};
        const depPath16 = {json.dumps(dep_path_16)};
        const depPath34 = {json.dumps(dep_path_34)};
        const apiKey = "{api_key}";

        // App State
        let currentSpot = spots[0];
        let planeLat = 33.585;
        let planeLng = 130.445;
        let simDay = "本日";
        let simHour = 12;
        let windDir = 160;
        let windSpeed = 6;
        let currentRwy = "16";
        let filterRwy = "すべて";

        // Map Setup
       const map = L.map('map', {{ zoomControl: false, attributionControl: false }}).setView([33.560, 130.460], 12);
        L.control.zoom({{ position: 'bottomright' }}).addTo(map);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: 'Esri', maxZoom: 19
        }}).addTo(map);

        let markersLayer = L.layerGroup().addTo(map);
        let approachLayer = null;
        let departureLayer = null;

        // Interactive Map Click (Warp)
        map.on('click', function(e) {{
            planeLat = e.latlng.lat;
            planeLng = e.latlng.lng;
            renderMapElements();
        }});

        function getPlaneSvg(heading) {{
            return `
            <div class="ghost-marker" style="width: 72px; height: 72px;">
                <svg width="72" height="72" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(2px 4px 6px rgba(0,0,0,0.8));">
                    <g style="transform: rotate(${{heading}}deg); transform-origin: 12px 12px;">
                        <path d="M21 16v-2l-8-5V3.5C13 2.67 12.33 2 11.5 2S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z" fill="#E0E0E0" stroke="#111111" stroke-width="0.5"/>
                    </g>
                </svg>
            </div>`;
        }}

        function getCameraSvg(isSelected) {{
            let color = isSelected ? "#81ecff" : "#444756";
            return `
            <div style="width: 24px; height: 24px; margin-left: -12px; margin-top: -12px;">
                <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(1px 2px 3px rgba(0,0,0,0.5));">
                    <circle cx="12" cy="12" r="11" fill="${{color}}" stroke="#0a0e1a" stroke-width="2"/>
                    <path d="M 8 10 L 9.5 8.5 L 14.5 8.5 L 16 10 L 17 10 A 1 1 0 0 1 18 11 L 18 16 A 1 1 0 0 1 17 17 L 7 17 A 1 1 0 0 1 6 16 L 6 11 A 1 1 0 0 1 7 10 Z" fill="#0a0e1a"/>
                    <circle cx="12" cy="13.5" r="2.5" fill="${{color}}"/>
                </svg>
            </div>`;
        }}

        function renderMapElements() {{
            markersLayer.clearLayers();

            // 1. Wind Indicator (Fixed HUD Overlay)
            let animSpeed = Math.max(0.4, 2.5 - (windSpeed * 0.15)); 
            let windSvg = `
            <div style="width: 80px; height: 80px; filter: drop-shadow(0 0 10px rgba(129,236,255,0.8));">
                <svg width="80" height="80" viewBox="0 0 80 80" style="transform: rotate(${{windDir}}deg);">
                    <style>
                        @keyframes windFlow {{
                            0% {{ transform: translateY(-20px); opacity: 0; }}
                            20% {{ opacity: 1; }}
                            80% {{ opacity: 1; }}
                            100% {{ transform: translateY(20px); opacity: 0; }}
                        }}
                        .w-line1 {{ animation: windFlow ${{animSpeed}}s linear infinite; }}
                        .w-line2 {{ animation: windFlow ${{animSpeed * 1.3}}s linear infinite 0.2s; opacity: 0.6; }}
                        .w-line3 {{ animation: windFlow ${{animSpeed * 0.8}}s linear infinite 0.4s; opacity: 0.6; }}
                    </style>
                    <circle cx="40" cy="40" r="30" fill="none" stroke="#81ecff" stroke-width="1" stroke-dasharray="2, 4" opacity="0.3" />
                    <circle cx="40" cy="40" r="15" fill="none" stroke="#81ecff" stroke-width="1" stroke-dasharray="2, 4" opacity="0.5" />
                    <circle cx="40" cy="40" r="2" fill="#81ecff" />
                    
                    <g fill="none" stroke="#81ecff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path class="w-line1" d="M40,20 L40,60 M34,54 L40,60 L46,54" />
                        <path class="w-line2" d="M26,25 L26,55 M22,51 L26,55 L30,51" />
                        <path class="w-line3" d="M54,30 L54,50 M50,46 L54,50 L58,46" />
                    </g>
                </svg>
            </div>`;
            // マーカーではなく、画面固定のHUDレイヤーに直接HTMLを注入する
            document.getElementById('wind-hud').innerHTML = windSvg;

            let windIcon = L.divIcon({{
                html: windSvg,
                className: '', iconSize: [80, 80]
            }});
            L.marker([33.585, 130.445], {{icon: windIcon, interactive: false}}).addTo(markersLayer);

            // 2. Camera Spots
            let firstSpotSet = false;
            spots.forEach(spot => {{
                if (filterRwy !== "すべて" && !spot['RWY'].includes(filterRwy)) return;
                
                if (!firstSpotSet && !spots.some(s => s['スポット'] === currentSpot['スポット'] && (filterRwy === "すべて" || s['RWY'].includes(filterRwy)))) {{
                    currentSpot = spot;
                }}
                firstSpotSet = true;

                let isSelected = (spot['スポット'] === currentSpot['スポット']);
                let icon = L.divIcon({{ html: getCameraSvg(isSelected), className: '' }});
                
                let marker = L.marker([spot['緯度'], spot['経度']], {{icon: icon}}).bindTooltip(spot['スポット']);
                marker.on('click', (e) => {{
                    L.DomEvent.stopPropagation(e); // Prevent map click from moving plane
                    currentSpot = spot;
                    updateUI();
                    renderMapElements();
                }});
                marker.addTo(markersLayer);
            }});

            // 3. Sightline
            L.polyline([[currentSpot['緯度'], currentSpot['経度']], [planeLat, planeLng]], {{
                color: '#81ecff', weight: 3, dashArray: '5, 8'
            }}).addTo(markersLayer);

            // 4. Airplane
            let heading = currentRwy === "16" ? 150 : 330;
            let planeIcon = L.divIcon({{ html: getPlaneSvg(heading), className: '' }});
            L.marker([planeLat, planeLng], {{icon: planeIcon, interactive: false}}).addTo(markersLayer);
        }}

        function updateAntPath() {{
            // 既存のルートがあれば消去
            if (approachLayer) map.removeLayer(approachLayer);
            if (departureLayer) map.removeLayer(departureLayer);
            
            // 使用滑走路に応じたルート座標の取得
            let appCoords = currentRwy === "16" ? path16 : path34;
            let depCoords = currentRwy === "16" ? depPath16 : depPath34;
            
            // 色の設定（着陸：シアン、離陸：オレンジ）
            let appColor = currentRwy === "16" ? "#81ecff" : "#00e3fd";
            let depColor = "#ffaa00"; 
            
            // アプローチ（着陸）ルートの描画
            approachLayer = L.polyline.antPath(appCoords, {{ delay: 800, weight: 6, color: appColor, pulseColor: "#ffffff" }});
            approachLayer.bindTooltip("🛬 アプローチ（着陸）ルート", {{sticky: true}});
            approachLayer.addTo(map);

            // ディパーチャー（離陸）ルートの描画
            departureLayer = L.polyline.antPath(depCoords, {{ delay: 800, weight: 6, color: depColor, pulseColor: "#ffffff" }});
            departureLayer.bindTooltip("🛫 ディパーチャー（離陸）ルート", {{sticky: true}});
            departureLayer.addTo(map);
        }}

        function updateUI() {{
            document.getElementById('spotName').innerText = currentSpot['スポット'];
            document.getElementById('spotDesc').innerText = currentSpot['特徴'];
            document.getElementById('spotTime').innerText = currentSpot['ベスト時間'];
            document.getElementById('spotLens').innerText = currentSpot['焦点距離'];
            
            document.getElementById('wDir').innerText = windDir + '°';
            document.getElementById('wSpd').innerText = windSpeed + ' kt';
            document.getElementById('cRwy').innerText = 'RWY ' + currentRwy;
            document.getElementById('cTime').innerText = simDay + ' ' + String(simHour).padStart(2, '0') + ':00';
        }}

        async function updateWeather() {{
            try {{
                const url = "https://api.open-meteo.com/v1/forecast?latitude=33.585&longitude=130.445&hourly=winddirection_10m,windspeed_10m&timezone=Asia%2FTokyo";
                const res = await fetch(url);
                const data = await res.json();
                
                // ▼ 修正：日本時間(JST)の正確な日付文字列を生成する
                let jstDate = new Date(new Date().toLocaleString("en-US", {{timeZone: "Asia/Tokyo"}}));
                if (simDay === "明日") {{
                    jstDate.setDate(jstDate.getDate() + 1);
                }}
                
                let yyyy = jstDate.getFullYear();
                let mm = String(jstDate.getMonth() + 1).padStart(2, '0');
                let dd = String(jstDate.getDate()).padStart(2, '0');
                let hh = String(simHour).padStart(2, '0');
                
                // APIのフォーマット(YYYY-MM-DDTHH:00)にピタリと合わせる
                let targetTimeStr = `${{yyyy}}-${{mm}}-${{dd}}T${{hh}}:00`;
                let idx = data.hourly.time.indexOf(targetTimeStr);
                
                if (idx !== -1) {{
                    windDir = data.hourly.winddirection_10m[idx];
                    windSpeed = Math.round(data.hourly.windspeed_10m[idx] * 0.539957); // km/h を kt に変換
                }} else {{ 
                    fallbackWeather(); 
                }}
            }} catch(e) {{ 
                fallbackWeather(); 
            }}
            
            // 風向から運用滑走路を判定 (90度〜270度の南風なら16、それ以外は34)
            currentRwy = (windDir >= 90 && windDir <= 270) ? "16" : "34";
            
            updateUI();
            renderMapElements();
            updateAntPath();
        }}

        function fallbackWeather() {{
            currentRwy = (simHour >= 7 && simHour <= 11) ? "16" : "34";
            windDir = currentRwy === "16" ? 160 : 340;
            windSpeed = currentRwy === "16" ? 6 : 18;
        }}

        async function requestBriefing() {{
            if (!apiKey) {{
                document.getElementById('ai-briefing').innerHTML = "🚨 <b>通信エラー:</b><br>GEMINI_API_KEY が設定されていません。";
                return;
            }}
            document.getElementById('ai-briefing').innerText = "ANALYZING TACTICAL DATA...";
            let heading = currentRwy === "16" ? 156 : 336;
            const prompt = `福岡空港の撮影スポット「${{currentSpot['スポット']}}」での空撮助言。シミュレーション予定日時は「${{simDay}}の${{simHour}}時」、風向は${{windDir}}度で風速は${{windSpeed}}kt。被写体の飛行機はRWY${{currentRwy}}運用に従い機首を${{heading}}度に向けています。この場所の特徴は「${{currentSpot['特徴']}}」、マスターの持参する推奨焦点距離は「${{currentSpot['焦点距離']}}」です。この機材と環境を活かしたマニアックな撮影戦術を解説せよ。Markdown記号は禁止。`;
            
            try {{
                const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${{apiKey}}`;
                const res = await fetch(url, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{contents: [{{parts: [{{text: prompt}}]}}]}})
                }});
                const data = await res.json();
                document.getElementById('ai-briefing').innerText = data.candidates[0].content.parts[0].text;
            }} catch (e) {{
                document.getElementById('ai-briefing').innerHTML = "🚨 <b>AIシステムとの通信に失敗しました。</b><br>ネットワーク環境を確認してください。";
            }}
        }}

        // Handle user input controls
        function changeFilter(val) {{ filterRwy = val; renderMapElements(); }}
        function changeDay(val) {{ simDay = val; updateWeather(); }}
        function changeHourLive(val) {{ document.getElementById('hourVal').innerText = val + ":00"; }}
        function changeHour(val) {{ simHour = parseInt(val); updateWeather(); }}

        // Initial Boot
        updateWeather();
    </script>
</body>
</html>
"""

# Streamlitの全画面を使って独自のUIを出力
st.components.v1.html(html_app, height=1100, scrolling=True)
