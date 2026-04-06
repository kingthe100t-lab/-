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
dep_path_16 = create_smooth_path([rwy34_pos, [33.57358529746922, 130.45909427227912], [33.57099367493191, 130.46089182237256], [33.54943579810327, 130.47855674420796]], 60)
dep_path_34 = create_smooth_path([rwy16_pos, [33.59742619248169, 130.4428436113514], [33.61313, 130.43086], [33.63183125340424, 130.41670130435546]], 60)

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
    <style>
        html, body {{ background: #04060d; color: #e2e4f6; font-family: 'Manrope', sans-serif; margin: 0; padding: 0; height: 100%; overflow: hidden; position: fixed; width: 100%; }}
        
        /* ▼ サイバーなドット背景 */
        .app-container {{ 
            position: absolute; inset: 0; overflow-y: auto; -webkit-overflow-scrolling: touch; padding: 1.5rem; 
            background-image: 
                radial-gradient(circle, rgba(129, 236, 255, 0.7) 0.6px, transparent 0.7px),
                radial-gradient(circle, rgba(129, 236, 255, 0.15) 1px, transparent 2px),
                linear-gradient(to bottom right, #020308, #0a0e1a, #020308); 
            background-size: 35px 35px, 35px 35px, 100% 100%;
        }}
        
        .glass-panel {{ background: rgba(15, 20, 35, 0.6); backdrop-filter: blur(20px); border: 1px solid rgba(129, 236, 255, 0.2); border-radius: 12px; }}
        .neon-text {{ color: #81ecff; text-shadow: 0 0 15px rgba(129,236,255,0.6); font-family: 'Space Grotesk', sans-serif; }}
        /* 既存のCSSコードが並んでいる場所です... */
        .cyber-btn {{ background: linear-gradient(90deg, #81ecff, #00e3fd); color: #004d57; font-weight: 700; border-radius: 6px; }}
        
        /* ▼▼▼ 地図を明るくするための修正ブロック ▼▼▼ */
        /* 地図タイルの輝度とコントラストを上げる */
        .leaflet-tile-container {{
            filter: brightness(110%) contrast(115%);
        }}
        /* mix-blend-mode: screen で地図に明るさを加算 */
        .leaflet-container {{
            background: #0a101f !important; /* 背景色も少し明るく */
            outline: none !important;
        }}
        .leaflet-container * {{ outline: none !important; -webkit-tap-highlight-color: transparent !important; }}
        /* ▲▲▲ ここまで ▲▲▲ */
        
        input[type=range] {{ -webkit-appearance: none; background: rgba(129,236,255,0.2); height: 4px; border-radius: 2px; width: 100%; }}
        input[type=range]::-webkit-slider-thumb {{ -webkit-appearance: none; height: 18px; width: 18px; border-radius: 50%; background: #81ecff; box-shadow: 0 0 10px #81ecff; cursor: pointer; }}

        /* 太陽HUDの背景を少し明るく */
        #wind-hud {{
            background: rgba(30, 45, 70, 0.8) !important;
            border: 1px solid rgba(129, 236, 255, 0.4) !important;
        }}

        /* ▼▼▼ 光の層の見た目を変更 ▼▼▼ */
        #sun-glow-overlay {{
            transition: background 0.5s ease;
            mix-blend-mode: screen; /* overlay から screen に変更して明るさを加算 */
            z-index: 400;
            opacity: 1.0; /* 不透明度を上げる */
        }}
        /* ▲▲▲ ここまで ▲▲▲ */

        /* ▼ スマホ・タブレット用（768px以下）の縮小ルール */
        @media (max-width: 768px) {{
            #wind-hud {{
                transform: scale(0.6);
                transform-origin: bottom left;
                margin-left: -10px;
                margin-bottom: -10px;
            }}
            .leaflet-marker-icon > div {{
                transform: scale(0.7);
                transform-origin: center center;
            }}
        }}
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
                    
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div class="glass-panel p-3 flex flex-col gap-1">
                            <span class="text-[#81ecff] text-[9px] font-bold tracking-widest">DAY</span>
                            <div class="flex gap-2 text-[10px] text-white">
                                <label class="flex items-center gap-1 cursor-pointer"><input type="radio" name="day" value="本日" checked onchange="changeDay(this.value)"> TODAY</label>
                                <label class="flex items-center gap-1 cursor-pointer"><input type="radio" name="day" value="明日" onchange="changeDay(this.value)"> TOMORROW</label>
                            </div>
                        </div>

                        <div class="glass-panel p-3 flex flex-col gap-1 border-l-2 border-[#ffaa00]">
                            <span class="text-[#ffaa00] text-[9px] font-bold tracking-widest">OPS MODE</span>
                            <div class="flex gap-2 text-[10px] text-white">
                                <label class="flex items-center gap-1 cursor-pointer"><input type="radio" name="ops" value="AUTO" checked onchange="changeOpsMode(this.value)"> AUTO</label>
                                <label class="flex items-center gap-1 cursor-pointer"><input type="radio" name="ops" value="16" onchange="changeOpsMode(this.value)"> FIX 16</label>
                                <label class="flex items-center gap-1 cursor-pointer"><input type="radio" name="ops" value="34" onchange="changeOpsMode(this.value)"> FIX 34</label>
                            </div>
                        </div>

                        <div class="glass-panel p-3 flex flex-col gap-1">
                            <span class="text-[#81ecff] text-[9px] font-bold tracking-widest">FILTER</span>
                            <div class="flex gap-2 text-[10px] text-white">
                                <label class="flex items-center gap-1 cursor-pointer"><input type="radio" name="rwy" value="すべて" checked onchange="changeFilter(this.value)"> ALL</label>
                                <label class="flex items-center gap-1 cursor-pointer"><input type="radio" name="rwy" value="16" onchange="changeFilter(this.value)"> 16</label>
                                <label class="flex items-center gap-1 cursor-pointer"><input type="radio" name="rwy" value="34" onchange="changeFilter(this.value)"> 34</label>
                            </div>
                        </div>

                        <div class="glass-panel p-3 flex flex-col gap-1">
                            <div class="flex justify-between text-[9px] text-[#81ecff] font-bold">
                                <span>TIMELINE</span>
                                <span id="hourVal" class="text-white">12:00</span>
                            </div>
                            <input type="range" min="7" max="22" value="12" oninput="changeHourLive(this.value)" onchange="changeHour(this.value)">
                        </div>
                    </div>
                    
                    <div class="glass-panel p-4 grid grid-cols-5 gap-2 text-center text-[10px] tracking-tighter">
                        <div><div class="text-[#a7aabb]">天気</div><div class="text-base font-bold text-white whitespace-nowrap" id="wCond">--</div></div>
                        <div><div class="text-[#a7aabb]">風向</div><div class="text-lg font-bold text-white" id="wDir">--</div></div>
                        <div><div class="text-[#a7aabb]">風速</div><div class="text-lg font-bold text-white" id="wSpd">--</div></div>
                        <div><div class="text-[#a7aabb]">運用滑走路</div><div class="text-lg font-bold text-[#00e3fd]" id="cRwy">--</div></div>
                        <div><div class="text-[#a7aabb]">予定</div><div class="text-lg font-bold text-white" id="cTime">--</div></div>
                    </div>

                    <div class="relative w-full h-[400px] lg:h-[600px]">
                        <div id="map" class="absolute inset-0 rounded-xl border border-[#81ecff]/30 shadow-2xl"></div>
                        <div id="sun-glow-overlay" style="position: absolute; inset: 0; pointer-events: none; border-radius: 12px;"></div>
                        <div id="wind-hud" class="absolute bottom-6 left-6 z-[400] pointer-events-none"></div>
                        
                        <div id="real-wind-hud" class="absolute top-4 right-4 z-[400] pointer-events-none glass-panel p-3 flex flex-col items-center justify-center gap-1 shadow-lg border border-[#ffaa00]/40" style="background: rgba(10,14,26,0.8);">
                            <span class="text-[9px] text-[#ffaa00] font-bold tracking-widest uppercase">WIND</span>
                            <div style="width: 36px; height: 36px; position: relative; display: flex; align-items: center; justify-content: center;">
                                <svg id="wind-arrow" width="28" height="28" viewBox="0 0 24 24" style="transition: transform 0.5s ease; filter: drop-shadow(0 0 5px #ffaa00);">
                                    <path d="M12 2L19 21l-7-4-7 4 7-19z" fill="#ffaa00" />
                                </svg>
                            </div>
                            <span id="wind-dir-text" class="text-white text-xs font-bold font-mono">--°</span>
                        </div>
                        </div>
                </div>

                <div class="lg:col-span-5 flex flex-col gap-4">
                    <div class="glass-panel p-6 border-l-4 border-[#81ecff]">
                        <div class="text-[#81ecff] text-[10px] font-bold tracking-widest uppercase mb-1">Spot Analysis</div>
                        <h3 class="text-2xl font-bold mb-4 text-white" id="spotName">--</h3>
                        <p id="spotDesc" class="text-sm leading-relaxed mb-4 text-[#e2e4f6]">--</p>
                        <div class="grid grid-cols-2 gap-4 text-xs">
    <div><span class="text-[#a7aabb] block mb-1">BEST TIME</span><span id="spotTime" class="text-white font-bold text-sm">--</span></div>
    <div><span class="text-[#a7aabb] block mb-1">FOCAL LENGTH</span><span id="spotLens" class="text-white font-bold text-sm">--</span></div>
</div>
                    </div>
                    <div class="glass-panel p-6 flex-1 flex flex-col gap-4 min-h-[300px]">
                        <h3 class="text-[#81ecff] font-bold text-sm tracking-widest">TACTICAL BRIEFING</h3>
                        <button class="cyber-btn w-full py-3 text-sm" onclick="requestBriefing()">GET AI ADVICE</button>
                        <div id="ai-briefing" class="text-xs leading-relaxed overflow-y-auto flex-1 bg-black/30 p-4 rounded border border-white/5 text-white">Waiting for request...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const spots = {df_spots.to_json(orient="records")};
        const path16 = {json.dumps(path_16)}; const path34 = {json.dumps(path_34)};
        const depPath16 = {json.dumps(dep_path_16)}; const depPath34 = {json.dumps(dep_path_34)};
        const apiKey = "{api_key}";

        let currentSpot = spots[0], planeLat = 33.585, planeLng = 130.445;
        let simDay = "本日", simHour = 12, windDir = 160, windSpeed = 6, weatherCond = "--";
        let currentRwy = "16", filterRwy = "すべて", opsMode = "AUTO";

        const map = L.map('map', {{ zoomControl: false, attributionControl: false }}).setView([33.560, 130.460], 13);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}').addTo(map);
        let markersLayer = L.layerGroup().addTo(map), approachLayer = null, departureLayer = null;

        map.on('click', (e) => {{ planeLat = e.latlng.lat; planeLng = e.latlng.lng; renderMapElements(); }});

        function determineRunway(newDir, newSpeed) {{
            if (opsMode !== "AUTO") return opsMode;
            if (newSpeed <= 5 && currentRwy) return currentRwy;
            return (newDir >= 90 && newDir <= 270) ? "16" : "34";
        }}

        // --- 穴対策：影のフィルターを完全に廃止し、安全な発光に変更 ---
        function getShadowFilter(isGlow) {{ return ""; }}

        function getPlaneSvg(heading) {{
            return `<div style="width:65px; height:65px;"><svg width="65" height="65" viewBox="0 0 24 24"><g transform="rotate(${{heading}} 12 12)"><path d="M21 16v-2l-8-5V3.5C13 2.67 12.33 2 11.5 2S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z" fill="#81ecff"/></g></svg></div>`;
        }}

        function getCameraSvg(sel) {{
            let col = sel ? "#81ecff" : "#b0b3c2";
            // box-shadowなら「黒い穴」バグは絶対に起きません
            let glow = sel ? "box-shadow: 0 0 15px 2px #81ecff; border-radius: 50%;" : "";
            return `<div style="width:28px; height:28px; margin-left:-14px; margin-top:-14px; ${{glow}}"><svg width="28" height="28" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="${{col}}" stroke="#0a0e1a" stroke-width="2"/><path d="M8 10l1.5-1.5h5L16 10h1a1 1 0 011 1v5a1 1 0 01-1 1H7a1 1 0 01-1-1v-5a1 1 0 011-1z" fill="#1a1e2d"/><circle cx="12" cy="13.5" r="2.5" fill="${{col}}"/></svg></div>`;
        }}

        // --- 天気・実況・AI連携 ---
        async function updateWeather() {{
            const isRealtime = (simDay === "本日" && simHour === new Date().getHours());
            try {{
                if (isRealtime) {{
                    const res = await fetch(`https://aviationweather.gov/api/data/metar?ids=RJFF&format=json`);
                    const data = await res.json();
                    if (data.length > 0) {{ windDir = data[0].windDir || 160; windSpeed = data[0].windSpeed || 5; weatherCond = "📡METAR実況"; }}
                }} else {{
                    const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=33.585&longitude=130.445&hourly=winddirection_10m,windspeed_10m,weathercode&timezone=Asia%2FTokyo`);
                    const data = await res.json();
                    let tStr = `${{new Date().getFullYear()}}-${{String(new Date().getMonth()+1).padStart(2,'0')}}-${{String(new Date().getDate() + (simDay==="明日"?1:0)).padStart(2,'0')}}T${{String(simHour).padStart(2,'0')}}:00`;
                    let idx = data.hourly.time.indexOf(tStr);
                    if (idx !== -1) {{ windDir = data.hourly.winddirection_10m[idx]; windSpeed = Math.round(data.hourly.windspeed_10m[idx]*0.54); weatherCond = "☀️予報"; }}
                }}
            }} catch(e) {{ console.error(e); }}
            currentRwy = determineRunway(windDir, windSpeed);
            updateUI(); renderMapElements();
        }}

        async function requestBriefing() {{
            const briefingEl = document.getElementById('ai-briefing');
            briefingEl.innerText = "STRATEGIZING WITH 2.5 FLASH...";
            
            const prompt = `福岡空港の「${{currentSpot['スポット']}}」での撮影アドバイス。${{simDay}}${{simHour}}時、天気は${{weatherCond}}、風向${{windDir}}度、RWY${{currentRwy}}運用。焦点距離${{currentSpot['焦点距離']}}。短くマニアックに。`;
            
            try {{
                // 2.5 Flash専用のURL（v1betaを使用）
                const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${{apiKey}}`;
                
                const res = await fetch(url, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ contents: [{{ parts: [{{ text: prompt }}] }}] }})
                }});
                const data = await res.json();
                
                if (data.candidates && data.candidates[0].content.parts[0].text) {{
                    briefingEl.innerText = data.candidates[0].content.parts[0].text;
                }} else if (data.error) {{
                    // エラーが出た場合はその内容を詳しく表示
                    briefingEl.innerHTML = `<span style='color:#ffaa00;'>⚠️ AIエラー: ${{data.error.message}}</span>`;
                }} else {{
                    briefingEl.innerText = "応答が空でした。";
                }}
            }} catch(e) {{
                briefingEl.innerHTML = `<span style='color:#ffaa00;'>⚠️ 通信エラー: ${{e.message}}</span>`;
            }}
        }}

        // --- UI & 描画（省略なしの統合版） ---
        function updateUI() {{
            document.getElementById('spotName').innerText = currentSpot['スポット'];
            document.getElementById('spotDesc').innerText = currentSpot['特徴'];
            document.getElementById('wDir').innerText = windDir+'°'; 
            document.getElementById('wSpd').innerText = windSpeed+'kt';
            document.getElementById('cRwy').innerText = 'RWY '+currentRwy; 
            document.getElementById('cTime').innerText = simDay+' '+simHour+':00';
            document.getElementById('wCond').innerText = weatherCond;
            let arrow = document.getElementById('wind-arrow'); if(arrow) arrow.style.transform = `rotate(${{windDir + 180}}deg)`;
        }}

        function renderMapElements() {{
            markersLayer.clearLayers();
            spots.forEach(spot => {{
                if (filterRwy !== "すべて" && !spot['RWY'].includes(filterRwy)) return;
                let isSel = (spot['スポット'] === currentSpot['スポット']);
                L.marker([spot['緯度'], spot['経度']], {{ icon: L.divIcon({{ html: getCameraSvg(isSel), className: '' }}) }}).addTo(markersLayer).on('click', (e) => {{ e.originalEvent.stopPropagation(); currentSpot=spot; updateUI(); renderMapElements(); }});
            }});
            L.marker([planeLat, planeLng], {{ icon: L.divIcon({{ html: getPlaneSvg(currentRwy === "16" ? 150 : 330), className: '', iconAnchor: [22, 22] }}), interactive: false }}).addTo(markersLayer);
            if (approachLayer) map.removeLayer(approachLayer); if (departureLayer) map.removeLayer(departureLayer);
            approachLayer = L.polyline.antPath(currentRwy==="16"?path16:path34, {{delay:800,weight:5,color:'#81ecff'}}).addTo(map);
            departureLayer = L.polyline.antPath(currentRwy==="16"?depPath16:depPath34, {{delay:1000,weight:5,color:'#ffaa00'}}).addTo(map);
        }}

        function changeOpsMode(v) {{ opsMode = v; updateWeather(); }}
        function changeFilter(v) {{ filterRwy = v; renderMapElements(); }}
        function changeDay(v) {{ simDay = v; updateWeather(); }}
        function changeHourLive(v) {{ document.getElementById('hourVal').innerText = v+":00"; }}
        function changeHour(v) {{ simHour = parseInt(v); updateWeather(); }}

        updateWeather();
    </script>
</body>
</html>
"""
st.components.v1.html(html_app, height=1200, scrolling=False)
