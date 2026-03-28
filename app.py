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
        html, body {{ background: #04060d; ... }} /* 既存のコード */
        .app-container {{ ... }} /* 既存のコード */

        /* ▼ ここに以下の3行を追記してください ▼ */
        #sun-glow-overlay {{
            transition: background 0.5s ease;
            mix-blend-mode: screen;
            z-index: 400;
        }}
        /* ▲ ここまで ▲ */

        .glass-panel {{ ... }} /* 既存のコード */
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
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="glass-panel p-4 flex items-center gap-4">
                            <span class="text-[#81ecff] text-xs font-bold tracking-widest">RWY FILTER</span>
                            <div class="flex gap-3 text-sm">
                                <label><input type="radio" name="rwy" value="すべて" checked onchange="changeFilter(this.value)"> ALL</label>
                                <label><input type="radio" name="rwy" value="16" onchange="changeFilter(this.value)"> 16</label>
                                <label><input type="radio" name="rwy" value="34" onchange="changeFilter(this.value)"> 34</label>
                            </div>
                        </div>
                        <div class="glass-panel p-4 flex flex-col gap-2">
                            <div class="flex justify-between text-xs text-[#81ecff] font-bold"><span>TIMELINE</span><span id="hourVal">12:00</span></div>
                            <input type="range" min="7" max="22" value="12" oninput="changeHourLive(this.value)" onchange="changeHour(this.value)">
                        </div>
                    </div>
                    
                    <div class="glass-panel p-4 grid grid-cols-4 gap-2 text-center text-[10px] tracking-tighter">
                        <div><div class="text-[#a7aabb]">風向</div><div class="text-lg font-bold" id="wDir">--</div></div>
                        <div><div class="text-[#a7aabb]">風速</div><div class="text-lg font-bold" id="wSpd">--</div></div>
                        <div><div class="text-[#a7aabb]">運用滑走路</div><div class="text-lg font-bold text-[#00e3fd]" id="cRwy">--</div></div>
                        <div><div class="text-[#a7aabb]">予定</div><div class="text-lg font-bold" id="cTime">--</div></div>
                    </div>

                    <div class="relative w-full h-[400px] lg:h-[600px]">
                        <div id="map" class="absolute inset-0 rounded-xl border border-[#81ecff]/30 shadow-2xl"></div>
                        <div id="sun-glow-overlay" style="position: absolute; inset: 0; z-index: 400; pointer-events: none; border-radius: 12px;"></div>
                        <div id="wind-hud" class="absolute bottom-6 left-6 z-[400] pointer-events-none"></div>
                    </div>
                </div>

                <div class="lg:col-span-5 flex flex-col gap-4">
                    <div class="glass-panel p-6 border-l-4 border-[#81ecff]">
                        <div class="text-[#81ecff] text-[10px] font-bold tracking-widest uppercase mb-1">Spot Analysis</div>
                        <h3 class="text-2xl font-bold mb-4" id="spotName">--</h3>
                        <p id="spotDesc" class="text-sm leading-relaxed mb-4 text-[#e2e4f6]">--</p>
                        <div class="grid grid-cols-2 gap-4 text-xs">
                            <div><span class="text-[#a7aabb] block">BEST TIME</span><span id="spotTime">--</span></div>
                            <div><span class="text-[#a7aabb] block">FOCAL LENGTH</span><span id="spotLens">--</span></div>
                        </div>
                    </div>
                    <div class="glass-panel p-6 flex-1 flex flex-col gap-4 min-h-[300px]">
                        <h3 class="text-[#81ecff] font-bold text-sm tracking-widest">TACTICAL BRIEFING</h3>
                        <button class="cyber-btn w-full py-3 text-sm" onclick="requestBriefing()">GET AI ADVICE</button>
                        <div id="ai-briefing" class="text-xs leading-relaxed overflow-y-auto flex-1 bg-black/30 p-4 rounded border border-white/5">Waiting for request...</div>
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

        let currentSpot = spots[0], planeLat = 33.585, planeLng = 130.445, simDay = "本日", simHour = 12, windDir = 160, windSpeed = 6, currentRwy = "16", filterRwy = "すべて";

        // 地図初期化（クレジット・ズームコントロール非表示）
        const map = L.map('map', {{ zoomControl: false, attributionControl: false }}).setView([33.560, 130.460], 13);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}').addTo(map);
        
        let markersLayer = L.layerGroup().addTo(map), approachLayer = null, departureLayer = null;

        map.on('click', (e) => {{ planeLat = e.latlng.lat; planeLng = e.latlng.lng; renderMapElements(); }});

        // ☀️ 影のフィルタ計算（太陽の反対方向へ伸ばす）
        function getShadowFilter(isGlow) {{
            let t = (simHour - 6) / 12, angle = t * Math.PI;
            let isNight = simHour < 6 || simHour >= 18;
            // 影を長く(20px)して、光の方向を強調
            let dist = isNight ? 0 : 20; 
            let dx = -Math.cos(angle) * dist, dy = -Math.sin(angle) * dist;
            let glow = isGlow ? "drop-shadow(0 0 12px #81ecff) " : "";
            return `${{glow}}drop-shadow(${{dx}}px ${{dy}}px 6px rgba(0,0,0,0.8))`;
        }}

        // ✈️ 飛行機SVG (44px拡大版)
        function getPlaneSvg(heading) {{
            return `
            <div style="width:44px; height:44px;">
                <svg width="44" height="44" viewBox="0 0 24 24" style="filter:${{getShadowFilter(false)}}; transition:filter 0.3s ease;">
                    <g transform="rotate(${{heading}} 12 12)">
                        <path d="M21 16v-2l-8-5V3.5C13 2.67 12.33 2 11.5 2S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z" fill="#81ecff"/>
                    </g>
                </svg>
            </div>`;
        }}

        // 📸 カメラピンSVG
        function getCameraSvg(sel) {{
            let col = sel ? "#81ecff" : "#444756";
            return `
            <div style="width:28px; height:28px; margin-left:-14px; margin-top:-14px;">
                <svg width="28" height="28" viewBox="0 0 24 24" style="filter:${{getShadowFilter(sel)}}; transition:filter 0.3s ease;">
                    <circle cx="12" cy="12" r="11" fill="${{col}}" stroke="#0a0e1a" stroke-width="2"/>
                    <path d="M8 10l1.5-1.5h5L16 10h1a1 1 0 011 1v5a1 1 0 01-1 1H7a1 1 0 01-1-1v-5a1 1 0 011-1z" fill="#0a0e1a"/><circle cx="12" cy="13.5" r="2.5" fill="${{col}}"/>
                </svg>
            </div>`;
        }}

        // ☀️ ガチ太陽HUD計算 (福岡空港 北緯33.58)
        function getSunPositionHud(h) {{
            let date = new Date(); if (simDay === "明日") date.setDate(date.getDate() + 1);
            let dayOfYear = Math.floor((date - new Date(date.getFullYear(), 0, 0)) / 864e5);
            let decl = 23.45 * Math.sin((360/365)*(dayOfYear-81)*Math.PI/180)*Math.PI/180, lat = 33.58*Math.PI/180;
            let cosH0 = -Math.tan(lat)*Math.tan(decl), H0 = Math.acos(Math.max(-1,Math.min(1,cosH0)))*180/Math.PI;
            let rise = 12-H0/15, set = 12+H0/15, isNight = h < rise || h > set;
            function getX(h) {{ return 85 + (h-12)*12; }}
            function getY(h) {{ let ha = 15*(h-12)*Math.PI/180; return 90 - Math.asin(Math.sin(lat)*Math.sin(decl)+Math.cos(lat)*Math.cos(decl)*Math.cos(ha))*180/Math.PI; }}
            let archPath = `M${{getX(rise)}},90 `; for(let i=Math.ceil(rise); i<=Math.floor(set); i++) archPath+=`L${{getX(i)}},${{getY(i)}} `; archPath+=`L${{getX(set)}},90`;
            
            return `<div style="width:200px;height:130px;border-radius:12px;border:1px solid rgba(129,236,255,0.4);background:rgba(10,14,26,0.95);backdrop-filter:blur(10px);padding:5px;">
                <svg width="190" height="110" viewBox="-30 0 230 110">
                    <line x1="-30" y1="90" x2="200" y2="90" stroke="#81ecff" opacity="0.4"/>
                    <text x="${{getX(6)}}" y="104" fill="#81ecff" font-size="12" font-weight="900" text-anchor="middle">E</text>
                    <text x="${{getX(12)}}" y="104" fill="#81ecff" font-size="12" font-weight="900" text-anchor="middle">S</text>
                    <text x="${{getX(18)}}" y="104" fill="#81ecff" font-size="12" font-weight="900" text-anchor="middle">W</text>
                    <path d="${{archPath}}" fill="none" stroke="#ffaa00" stroke-width="2.5" opacity="${{isNight?0.2:0.8}}"/>
                    <circle cx="${{getX(h)}}" cy="${{isNight?90:getY(h)}}" r="5" fill="#fff" style="filter:drop-shadow(0 0 8px #ffaa00)" opacity="${{isNight?0:1}}"/>
                    <text x="85" y="75" fill="#81ecff" font-size="26" font-weight="900" text-anchor="middle" font-family="Space Grotesk" style="text-shadow:0 0 15px #81ecff">${{String(h).padStart(2,'0')}}:00</text>
                </svg>
            </div>`;
        }}

        // 🗺️ 全要素描画
        function renderMapElements() {{
            markersLayer.clearLayers();
            document.getElementById('wind-hud').innerHTML = getSunPositionHud(simHour);
            
            // ☀️ 画面全体へのオレンジ・グラデーション（太陽の方向に合わせる）
            let t = (simHour - 6) / 12;
            let isNight = simHour < 6 || simHour >= 18;
            let overlay = document.getElementById('sun-glow-overlay');
            
            if (isNight) {{
                overlay.style.background = "transparent";
            }} else {{
                // 太陽の方角（角度）を計算
                // 6時(E)=0度, 12時(S)=90度, 18時(W)=180度
                let angle = t * 180; 
                // CSSのlinear-gradientに変換（太陽がある方向から光が来るように）
                overlay.style.background = `linear-gradient(${{angle + 90}}deg, rgba(255, 170, 0, 0.25) 0%, transparent 70%)`;
            }}

            spots.forEach(spot => {{
                if (filterRwy !== "すべて" && !spot['RWY'].includes(filterRwy)) return;
                let marker = L.marker([spot['緯度'], spot['経度']], {{
                    icon: L.divIcon({{ html: getCameraSvg(spot['スポット'] === currentSpot['スポット']), className: '' }})
                }}).bindTooltip(spot['スポット']).addTo(markersLayer);
                marker.on('click', () => {{ currentSpot=spot; updateUI(); renderMapElements(); }});
            }});
            
            L.polyline([[currentSpot['緯度'],currentSpot['経度']],[planeLat,planeLng]],{{color:'#81ecff',weight:2,dashArray:'5,10',opacity:0.5}}).addTo(markersLayer);
            
            L.marker([planeLat,planeLng],{{
                icon:L.divIcon({{
                    html:getPlaneSvg(currentRwy==="16"?156:336),
                    className:'',
                    iconSize:[44,44],
                    iconAnchor:[22,22]
                }}),
                interactive: false
            }}).addTo(markersLayer);
            
            updateAntPath();
        }}

        // 🛣️ ルートアニメーション (Arrival & Departure)
        function updateAntPath() {{
            if (approachLayer) map.removeLayer(approachLayer); if (departureLayer) map.removeLayer(departureLayer);
            approachLayer = L.polyline.antPath(currentRwy==="16"?path16:path34, {{delay:800,weight:5,color:'#81ecff',pulseColor:'#fff'}}).addTo(map);
            departureLayer = L.polyline.antPath(currentRwy==="16"?depPath16:depPath34, {{delay:1000,weight:5,color:'#ffaa00',pulseColor:'#fff'}}).addTo(map);
        }}

        async function updateWeather() {{
            try {{
                const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=33.585&longitude=130.445&hourly=winddirection_10m,windspeed_10m&timezone=Asia%2FTokyo`);
                const data = await res.json();
                let now = new Date(new Date().toLocaleString("en-US", {{timeZone:"Asia/Tokyo"}})); if(simDay==="明日") now.setDate(now.getDate()+1);
                let target = `${{now.getFullYear()}}-${{String(now.getMonth()+1).padStart(2,'0')}}-${{String(now.getDate()).padStart(2,'0')}}T${{String(simHour).padStart(2,'0')}}:00`;
                let idx = data.hourly.time.indexOf(target);
                if(idx!==-1) {{ windDir=data.hourly.winddirection_10m[idx]; windSpeed=Math.round(data.hourly.windspeed_10m[idx]*0.54); }}
            }} catch(e) {{ windDir=160; windSpeed=6; }}
            currentRwy = (windDir>=90 && windDir<=270) ? "16" : "34";
            updateUI(); renderMapElements();
        }}

        function updateUI() {{
            document.getElementById('spotName').innerText = currentSpot['スポット'];
            document.getElementById('spotDesc').innerText = currentSpot['特徴'];
            document.getElementById('spotTime').innerText = currentSpot['ベスト時間'];
            document.getElementById('spotLens').innerText = currentSpot['焦点距離'];
            document.getElementById('wDir').innerText = windDir+'°'; document.getElementById('wSpd').innerText = windSpeed+'kt';
            document.getElementById('cRwy').innerText = 'RWY '+currentRwy; document.getElementById('cTime').innerText = simDay+' '+simHour+':00';
        }}

        async function requestBriefing() {{
            document.getElementById('ai-briefing').innerText = "STRATEGIZING...";
            const prompt = `福岡空港の「${{currentSpot['スポット']}}」での撮影アドバイス。${{simDay}}${{simHour}}時、風向${{windDir}}度、RWY${{currentRwy}}運用。焦点距離${{currentSpot['焦点距離']}}。短くマニアックに。`;
            try {{
                const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${{apiKey}}`, {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{contents:[{{parts:[{{text:prompt}}]}}]}})}});
                const data = await res.json(); document.getElementById('ai-briefing').innerText = data.candidates[0].content.parts[0].text;
            }} catch(e) {{ document.getElementById('ai-briefing').innerText = "OFFLINE"; }}
        }}

        function changeFilter(v) {{ filterRwy=v; renderMapElements(); }}
        function changeDay(v) {{ simDay=v; updateWeather(); }}
        function changeHourLive(v) {{ document.getElementById('hourVal').innerText = v+":00"; }}
        function changeHour(v) {{ simHour=parseInt(v); updateWeather(); }}
        
        // 初回起動
        updateWeather();
    </script>
</body>
</html>
"""
st.components.v1.html(html_app, height=1200, scrolling=False)
