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

# --- 🌐 超・本格的フロントエンド（HTML/JS/CSS）の構築 ---
html_app = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
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
        .leaflet-container {{ background: #0a0e1a; font-family: 'Manrope', sans-serif; }}
        .ghost-marker {{ pointer-events: none !important; background: transparent !important; border: none !important; margin-left: -12px !important; margin-top: -12px !important; }}
        .custom-radio input[type="radio"] {{ accent-color: #81ecff; cursor: pointer; filter: drop-shadow(0 0 7px #81ecff); }} 
    </style>
</head>
<body>
    <div class="app-container">
    <div class="max-w-[1400px] mx-auto flex flex-col gap-6 w-full">
        <h1 class="text-3xl font-black flex items-center gap-4 neon-text uppercase m-0">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21 16v-2l-8-5V3.5C13 2.67 12.33 2 11.5 2S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z" fill="#0088ff"/>
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

                <div id="map" class="w-full h-[350px] rounded-lg border border-[#81ecff]/30 shadow-[0_0_20px_rgba(0,229,255,0.1)] z-0"></div>
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
        const map = L.map('map', {{ zoomControl: false }}).setView([33.560, 130.460], 12);
        L.control.zoom({{ position: 'bottomright' }}).addTo(map);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: 'Esri', maxZoom: 19
        }}).addTo(map);

        let markersLayer = L.layerGroup().addTo(map);
        let antPathLayer = null;

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

            // 1. Wind Indicator
            let windIcon = L.divIcon({{
                html: `<div style="font-size: 35px; color: #81ecff; text-shadow: 2px 2px 4px #000; transform: rotate(${{windDir}}deg); transform-origin: center; margin-left: -20px; margin-top: -20px;">⬇</div>`,
                className: '', iconSize: [40, 40]
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
            if (antPathLayer) map.removeLayer(antPathLayer);
            let coords = currentRwy === "16" ? path16 : path34;
            let color = currentRwy === "16" ? "#81ecff" : "#00e3fd";
            antPathLayer = L.polyline.antPath(coords, {{ delay: 800, weight: 6, color: color, pulseColor: "#ffffff" }});
            antPathLayer.addTo(map);
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
                
                let targetDate = new Date();
                targetDate.setHours(targetDate.getHours() + 9);
                if (simDay === "明日") targetDate.setDate(targetDate.getDate() + 1);
                
                let isoStr = targetDate.toISOString().split('T')[0] + "T" + String(simHour).padStart(2, '0') + ":00";
                let idx = data.hourly.time.indexOf(isoStr);
                
                if (idx !== -1) {{
                    windDir = data.hourly.winddirection_10m[idx];
                    windSpeed = Math.round(data.hourly.windspeed_10m[idx] * 0.539957);
                }} else {{ fallbackWeather(); }}
            }} catch(e) {{ fallbackWeather(); }}
            
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
