from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import subprocess, os, json, psutil, threading, time, urllib.request
from datetime import datetime

app = Flask(__name__)
CORS(app)

try:
    from config import (LATITUDE, LONGITUDE, OWM_API_KEY, POLLEN_API_KEY, LOCATION_NAME)
except:
    LATITUDE, LONGITUDE = 33.73, 130.47
    OWM_API_KEY = ""
    POLLEN_API_KEY = ""
    LOCATION_NAME = "古賀市"

def get_system_info():
    try:
        temp_val = float(subprocess.check_output(["vcgencmd", "measure_temp"]).decode().strip().replace("temp=","").replace("'C",""))
    except:
        temp_val = 0
    try:
        volt_val = float(subprocess.check_output(["vcgencmd", "measure_volts"]).decode().strip().replace("volt=","").replace("V",""))
    except:
        volt_val = 0
    try:
        throttled_hex = int(subprocess.check_output(["vcgencmd", "get_throttled"]).decode().strip().replace("throttled=",""), 16)
        voltage_low = bool(throttled_hex & 0x1)
        throttled = bool(throttled_hex & 0x4)
    except:
        voltage_low = False
        throttled = False
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    return {
        "temp_val": temp_val, "temp": f"{temp_val:.1f}C",
        "volt_val": volt_val, "volt": f"{volt_val:.2f}V",
        "voltage_low": voltage_low, "throttled": throttled,
        "cpu": cpu,
        "mem_used": mem.used // 1024 // 1024,
        "mem_total": mem.total // 1024 // 1024,
        "mem_percent": mem.percent
    }

def get_weather_data():
    try:
        weather_map = {
            0:"快晴",1:"晴れ",2:"一部曇り",3:"曇り",45:"霧",48:"霧",
            51:"小雨",53:"雨",55:"大雨",61:"小雨",63:"雨",65:"大雨",
            71:"小雪",73:"雪",75:"大雪",80:"にわか雨",81:"雨",82:"大雨",
            95:"雷雨",96:"雷雨",99:"雷雨"
        }
        url = (f"https://api.open-meteo.com/v1/forecast"
               f"?latitude={LATITUDE}&longitude={LONGITUDE}"
               f"&current=temperature_2m,weathercode,windspeed_10m,relative_humidity_2m"
               f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode"
               f"&timezone=Asia%2FTokyo&forecast_days=3")
        with urllib.request.urlopen(url, timeout=5) as r:
            d = json.loads(r.read())
        current = d["current"]
        daily = d["daily"]
        w = lambda c: weather_map.get(c, "不明")

        pm25 = None
        pm25_level = "取得中"
        try:
            pm_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={LATITUDE}&lon={LONGITUDE}&appid={OWM_API_KEY}"
            with urllib.request.urlopen(pm_url, timeout=5) as r:
                pm_data = json.loads(r.read())
            pm25 = pm_data["list"][0]["components"]["pm2_5"]
            pm25_level = "良好" if pm25 < 12 else "普通" if pm25 < 35 else "悪い" if pm25 < 55 else "非常に悪い"
        except:
            pass

        pollen_data = []
        try:
            p_url = f"https://pollen.googleapis.com/v1/forecast:lookup?location.longitude={LONGITUDE}&location.latitude={LATITUDE}&days=1&key={POLLEN_API_KEY}"
            with urllib.request.urlopen(p_url, timeout=5) as r:
                pd = json.loads(r.read())
            cat_map = {"None":"なし","Very Low":"極少","Low":"少","Medium":"中","High":"多","Very High":"非常に多"}
            code_map = {"JAPANESE_CEDAR":"スギ","JAPANESE_CYPRESS":"ヒノキ","GRAMINALES":"イネ科"}
            level_map = {"None":0,"Very Low":1,"Low":2,"Medium":3,"High":4,"Very High":5}
            for plant in pd["dailyInfo"][0]["plantInfo"]:
                name = code_map.get(plant["code"], plant["displayName"])
                cat = plant["indexInfo"]["category"]
                val = plant["indexInfo"]["value"]
                if plant.get("inSeason", False) or val >= 2:
                    pollen_data.append({
                        "name": name, "level": level_map.get(cat, 0),
                        "label": cat_map.get(cat, cat), "value": val
                    })
        except:
            pass

        return {
            "ok": True,
            "current_temp": current["temperature_2m"],
            "current_weather": w(current["weathercode"]),
            "humidity": current["relative_humidity_2m"],
            "wind": current["windspeed_10m"],
            "tomorrow_weather": w(daily["weathercode"][1]),
            "tomorrow_max": daily["temperature_2m_max"][1],
            "tomorrow_min": daily["temperature_2m_min"][1],
            "tomorrow_rain": daily["precipitation_probability_max"][1],
            "day2_weather": w(daily["weathercode"][2]),
            "day2_max": daily["temperature_2m_max"][2],
            "day2_min": daily["temperature_2m_min"][2],
            "pm25": pm25, "pm25_level": pm25_level,
            "pollen": pollen_data
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def is_speaker_running():
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if 'smart_speaker.py' in ' '.join(proc.info.get('cmdline', [])):
                return True, proc.info['pid']
        except:
            pass
    return False, None

HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>ジェミニパイ</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#030d1a;--s:#071828;--b:#0d3455;--blue:#4dc8ff;--green:#00e5a0;--orange:#ffaa44;--red:#ff4466;--yellow:#ffdd44;--text:#c8e8ff;--muted:#3a6080}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{background:var(--bg);color:var(--text);font-family:'Noto Sans JP',sans-serif;padding:14px 12px 40px;max-width:480px;margin:0 auto}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 10% 10%,rgba(0,80,200,.06) 0%,transparent 60%),radial-gradient(ellipse at 90% 90%,rgba(0,180,120,.04) 0%,transparent 60%);pointer-events:none}
.hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--b)}
.logo{font-family:'Orbitron',monospace;font-size:16px;font-weight:900;color:var(--blue);letter-spacing:.12em}
.logo span{color:var(--green)}
.upd{font-size:9px;color:var(--muted);font-family:'Orbitron',monospace}
.ctrl{display:flex;gap:7px;margin-bottom:12px;flex-wrap:wrap}
.btn{padding:7px 12px;border:1px solid;border-radius:8px;font-family:'Orbitron',monospace;font-size:10px;font-weight:700;cursor:pointer;background:var(--s);display:flex;align-items:center;gap:4px;transition:opacity .15s;white-space:nowrap}
.btn:active{opacity:.65}
.ico{font-size:12px}
.g{border-color:var(--green);color:var(--green)}
.r{border-color:var(--red);color:var(--red)}
.o{border-color:var(--orange);color:var(--orange)}
.b{border-color:var(--blue);color:var(--blue)}
.card{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:12px;margin-bottom:10px;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--blue),var(--green))}
.status-row{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.dot{width:11px;height:11px;border-radius:50%;flex-shrink:0}
.online{background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 2s infinite}
.offline{background:var(--red);box-shadow:0 0 8px var(--red)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.slabel{font-family:'Orbitron',monospace;font-size:12px;font-weight:700}
.ssub{font-size:9px;color:var(--muted);margin-top:1px}
.volt-ok{color:var(--green)}
.volt-warn{color:var(--orange)}
.volt-bad{color:var(--red)}
.gauges{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.gauge{background:#040f1e;border:1px solid var(--b);border-radius:10px;padding:8px 6px;display:flex;flex-direction:column;align-items:center;gap:4px}
.gtitle{font-size:8px;color:var(--muted);font-family:'Orbitron',monospace}
.arc-w{position:relative;width:62px;height:34px}
.arc-w svg{width:62px;height:34px}
.arc-val{position:absolute;bottom:0;left:50%;transform:translateX(-50%);font-family:'Orbitron',monospace;font-size:11px;font-weight:700;white-space:nowrap}
.bar-w{width:100%;display:flex;flex-direction:column;gap:2px}
.bar-t{width:100%;height:5px;background:#0a1f35;border-radius:3px;overflow:hidden}
.bar-f{height:100%;border-radius:3px;transition:width .6s}
.bar-n{display:flex;justify-content:space-between;font-size:8px;color:var(--muted);font-family:'Orbitron',monospace}
.bar-pct{font-family:'Orbitron',monospace;font-size:13px;font-weight:700;text-align:center;margin-top:1px}
.wcard{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:12px;margin-bottom:10px;position:relative;overflow:hidden}
.wcard::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--blue),var(--yellow))}
.wsec{font-family:'Orbitron',monospace;font-size:9px;color:var(--muted);letter-spacing:.15em;margin-bottom:10px}
.wrow{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}
.wcell{background:#040f1e;border:1px solid var(--b);border-radius:10px;padding:10px 8px;text-align:center}
.wcell-title{font-size:9px;color:var(--muted);font-family:'Orbitron',monospace;margin-bottom:4px}
.wcell-val{font-family:'Orbitron',monospace;font-size:14px;font-weight:700;color:var(--blue)}
.wcell-sub{font-size:9px;color:var(--muted);margin-top:2px}
.env-row{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}
.env-cell{background:#040f1e;border:1px solid var(--b);border-radius:10px;padding:10px 8px}
.env-title{font-size:8px;color:var(--muted);font-family:'Orbitron',monospace;margin-bottom:6px}
.pm-val{font-family:'Orbitron',monospace;font-size:16px;font-weight:700;margin-bottom:4px}
.pm-label{font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;display:inline-block}
.pm-good{background:rgba(0,229,160,.15);color:var(--green);border:1px solid var(--green)}
.pm-mid{background:rgba(255,170,68,.15);color:var(--orange);border:1px solid var(--orange)}
.pm-bad{background:rgba(255,68,102,.15);color:var(--red);border:1px solid var(--red)}
.pollen-item{display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-bottom:1px solid var(--b);font-size:10px}
.pollen-item:last-child{border-bottom:none}
.pollen-bar-wrap{flex:1;margin:0 6px;height:4px;background:#0a1f35;border-radius:2px}
.pollen-bar{height:100%;border-radius:2px}
.pollen-lv{font-size:9px;font-family:'Orbitron',monospace;min-width:28px;text-align:right}
.frow{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.fcell{background:#040f1e;border:1px solid var(--b);border-radius:10px;padding:8px;text-align:center}
.fday{font-size:8px;color:var(--muted);font-family:'Orbitron',monospace;margin-bottom:4px}
.fweather{font-size:11px;color:var(--text);margin-bottom:2px}
.ftemp{font-family:'Orbitron',monospace;font-size:12px;font-weight:700;color:var(--blue)}
.frain{font-size:9px;color:var(--muted);margin-top:2px}
.sec{font-family:'Orbitron',monospace;font-size:9px;color:var(--muted);letter-spacing:.15em;margin-bottom:8px}
.logcard{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:12px}
.logcard::before{content:'';display:block;height:2px;background:linear-gradient(90deg,var(--orange),var(--blue));border-radius:1px;margin-bottom:10px}
.logitem{padding:8px 0;border-bottom:1px solid var(--b)}
.logitem:last-child{border-bottom:none}
.logq{font-size:11px;color:var(--blue);margin-bottom:2px}
.loga{font-size:10px;color:var(--muted);line-height:1.5}
.logt{font-size:8px;color:#1a3a50;margin-top:2px;font-family:'Orbitron',monospace}
.empty{font-size:11px;color:var(--muted);text-align:center;padding:16px}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(80px);background:#0d2a45;border:1px solid var(--blue);color:var(--blue);padding:9px 20px;border-radius:100px;font-size:11px;font-family:'Orbitron',monospace;transition:transform .3s;white-space:nowrap;z-index:999}
.toast.show{transform:translateX(-50%) translateY(0)}
</style>
</head>
<body>
<div class="hdr">
  <div><div class="logo">GEMINI<span>PI</span></div><div class="upd" id="upd">更新中...</div></div>
  <div style="font-size:22px">🤖</div>
</div>

<div class="ctrl">
  <button class="btn g" onclick="act('start')"><span class="ico">▶</span>起動</button>
  <button class="btn r" onclick="act('stop')"><span class="ico">⏹</span>停止</button>
  <button class="btn o" onclick="act('restart')"><span class="ico">🔄</span>再起動</button>
  <button class="btn b" onclick="doReboot()"><span class="ico">⚡</span>本体再起動</button>
</div>

<div class="card">
  <div class="status-row">
    <div class="dot" id="dot"></div>
    <div><div class="slabel" id="stxt">確認中...</div><div class="ssub" id="ssub"></div></div>
    <div style="margin-left:auto;text-align:right">
      <div id="volt" class="volt-ok" style="font-family:'Orbitron',monospace;font-size:13px;font-weight:700">--V</div>
      <div id="volt-label" style="font-size:9px;color:var(--muted)">電源電圧</div>
    </div>
  </div>
  <div class="gauges">
    <div class="gauge">
      <div class="gtitle">温度</div>
      <div class="arc-w">
        <svg viewBox="0 0 62 34">
          <path d="M6 32 A 24 24 0 0 1 56 32" fill="none" stroke="#0a1f35" stroke-width="6" stroke-linecap="round"/>
          <path id="arc-temp" d="M6 32 A 24 24 0 0 1 56 32" fill="none" stroke="#00e5a0" stroke-width="6" stroke-linecap="round" stroke-dasharray="75" stroke-dashoffset="75" style="transition:stroke-dashoffset .6s,stroke .4s"/>
        </svg>
        <div class="arc-val" id="val-temp" style="color:#00e5a0">--</div>
      </div>
    </div>
    <div class="gauge">
      <div class="gtitle">CPU</div>
      <div class="arc-w">
        <svg viewBox="0 0 62 34">
          <path d="M6 32 A 24 24 0 0 1 56 32" fill="none" stroke="#0a1f35" stroke-width="6" stroke-linecap="round"/>
          <path id="arc-cpu" d="M6 32 A 24 24 0 0 1 56 32" fill="none" stroke="#00e5a0" stroke-width="6" stroke-linecap="round" stroke-dasharray="75" stroke-dashoffset="75" style="transition:stroke-dashoffset .6s,stroke .4s"/>
        </svg>
        <div class="arc-val" id="val-cpu" style="color:#00e5a0">--</div>
      </div>
    </div>
    <div class="gauge" style="grid-column:span 2">
      <div class="gtitle">メモリ</div>
      <div class="bar-w" style="width:100%">
        <div class="bar-t"><div class="bar-f" id="bar-mem" style="width:0%;background:var(--green)"></div></div>
        <div class="bar-n"><span id="mem-used">--</span><span id="mem-total">--</span></div>
        <div class="bar-pct" id="val-mem" style="color:var(--green)">--%</div>
      </div>
    </div>
  </div>
</div>

<div class="wcard">
  <div class="wsec">WEATHER · 環境情報</div>
  <div class="wrow">
    <div class="wcell">
      <div class="wcell-title">現在の天気</div>
      <div class="wcell-val" id="cur-weather">--</div>
      <div class="wcell-sub" id="cur-temp">--℃</div>
    </div>
    <div class="wcell">
      <div class="wcell-title">湿度 / 風速</div>
      <div class="wcell-val" id="cur-humid">--%</div>
      <div class="wcell-sub" id="cur-wind">-- km/h</div>
    </div>
  </div>
  <div class="env-row">
    <div class="env-cell">
      <div class="env-title">PM2.5</div>
      <div class="pm-val" id="pm-val">--</div>
      <span class="pm-label" id="pm-label">取得中</span>
    </div>
    <div class="env-cell">
      <div class="env-title">花粉</div>
      <div id="pollen-list"><div style="font-size:10px;color:var(--muted)">取得中...</div></div>
    </div>
  </div>
  <div class="frow">
    <div class="fcell">
      <div class="fday">明日</div>
      <div class="fweather" id="tom-weather">--</div>
      <div class="ftemp" id="tom-temp">--/--℃</div>
      <div class="frain" id="tom-rain">降水 --%</div>
    </div>
    <div class="fcell">
      <div class="fday">明後日</div>
      <div class="fweather" id="d2-weather">--</div>
      <div class="ftemp" id="d2-temp">--/--℃</div>
    </div>
  </div>
</div>

<div class="sec">RECENT CONVERSATIONS</div>
<div class="logcard">
  <div id="logs"><div class="empty">まだ会話がありません</div></div>
</div>

<div class="toast" id="toast"></div>
<script>
const BASE=window.location.origin;
const ARC=75;
function clr(p){return p>80?'#ff4466':p>60?'#ffaa44':'#00e5a0';}
function setArc(id,vId,pct,lbl){
  const a=document.getElementById(id),e=document.getElementById(vId);
  a.style.strokeDashoffset=ARC-(ARC*Math.min(pct,100)/100);
  e.textContent=lbl;const c=clr(pct);a.style.stroke=c;e.style.color=c;
}
function setBar(p,u,t){
  const b=document.getElementById('bar-mem'),c=clr(p);
  b.style.width=p+'%';b.style.background=c;
  document.getElementById('mem-used').textContent=u+'M';
  document.getElementById('mem-total').textContent=t+'M';
  const e=document.getElementById('val-mem');e.textContent=Math.round(p)+'%';e.style.color=c;
}
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2500);}
async function fetchStatus(){
  try{
    const d=(await (await fetch(BASE+'/api/status')).json());
    document.getElementById('dot').className='dot '+(d.running?'online':'offline');
    document.getElementById('stxt').textContent=d.running?'稼働中':'停止中';
    document.getElementById('stxt').style.color=d.running?'#00e5a0':'#ff4466';
    document.getElementById('ssub').textContent=d.running?'PID: '+d.pid:'起動ボタンで再開';
    const s=d.system;
    setArc('arc-temp','val-temp',s.temp_val/85*100,s.temp_val.toFixed(1)+'℃');
    setArc('arc-cpu','val-cpu',s.cpu,s.cpu.toFixed(0)+'%');
    setBar(s.mem_percent,s.mem_used,s.mem_total);
    const ve=document.getElementById('volt'),vl=document.getElementById('volt-label');
    ve.textContent=s.volt;
    if(s.voltage_low){ve.className='volt-bad';vl.textContent='⚠️ 電圧不足';}
    else if(s.volt_val<4.9){ve.className='volt-warn';vl.textContent='△ 電圧低め';}
    else{ve.className='volt-ok';vl.textContent='✓ 電源正常';}
    document.getElementById('upd').textContent='更新: '+new Date().toLocaleTimeString('ja-JP');
  }catch(e){document.getElementById('stxt').textContent='接続エラー';}
}
async function fetchWeather(){
  try{
    const d=(await (await fetch(BASE+'/api/weather')).json());
    if(!d.ok)return;
    document.getElementById('cur-weather').textContent=d.current_weather;
    document.getElementById('cur-temp').textContent=d.current_temp+'℃';
    document.getElementById('cur-humid').textContent=d.humidity+'%';
    document.getElementById('cur-wind').textContent=d.wind+' km/h';
    const pv=document.getElementById('pm-val'),pl=document.getElementById('pm-label');
    if(d.pm25!==null){
      pv.textContent=d.pm25.toFixed(1)+' μg';
      pl.textContent=d.pm25_level;
      pl.className='pm-label '+(d.pm25<12?'pm-good':d.pm25<35?'pm-mid':'pm-bad');
    }
    const pol=document.getElementById('pollen-list');
    if(d.pollen&&d.pollen.length>0){
      pol.innerHTML=d.pollen.map(p=>`<div class="pollen-item"><span>${p.name}</span><div class="pollen-bar-wrap"><div class="pollen-bar" style="width:${p.level/5*100}%;background:${p.level<=1?'#00e5a0':p.level<=3?'#ffaa44':'#ff4466'}"></div></div><span class="pollen-lv" style="color:${p.level<=1?'#00e5a0':p.level<=3?'#ffaa44':'#ff4466'}">${p.label}</span></div>`).join('');
    }else{pol.innerHTML='<div style="font-size:10px;color:var(--green)">ほぼなし</div>';}
    document.getElementById('tom-weather').textContent=d.tomorrow_weather;
    document.getElementById('tom-temp').textContent=d.tomorrow_max+'/'+d.tomorrow_min+'℃';
    document.getElementById('tom-rain').textContent='降水 '+d.tomorrow_rain+'%';
    document.getElementById('d2-weather').textContent=d.day2_weather;
    document.getElementById('d2-temp').textContent=d.day2_max+'/'+d.day2_min+'℃';
  }catch(e){}
}
async function fetchLog(){
  try{
    const logs=(await (await fetch(BASE+'/api/log')).json());
    const el=document.getElementById('logs');
    if(!logs.length){el.innerHTML='<div class="empty">まだ会話がありません</div>';return;}
    el.innerHTML=logs.slice(-5).reverse().map(l=>`<div class="logitem"><div class="logq">Q: ${l.question}</div><div class="loga">${l.answer.substring(0,90)}${l.answer.length>90?'...':''}</div><div class="logt">${l.time}</div></div>`).join('');
  }catch(e){}
}
async function act(cmd){
  toast({start:'起動中...',stop:'停止中...',restart:'再起動中...'}[cmd]||'処理中...');
  try{const d=(await (await fetch(BASE+'/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:cmd})})).json());toast(d.message);setTimeout(fetchStatus,2000);}catch(e){toast('エラーが発生しました');}
}
function doReboot(){if(confirm('ラズパイ本体を再起動しますか？'))act('reboot');}
fetchStatus();fetchWeather();fetchLog();
setInterval(fetchStatus,10000);
setInterval(fetchWeather,300000);
setInterval(fetchLog,15000);
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/status')
def api_status():
    running, pid = is_speaker_running()
    return jsonify({"running":running,"pid":pid,"system":get_system_info(),"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

@app.route('/api/weather')
def api_weather():
    return jsonify(get_weather_data())

@app.route('/api/log')
def api_log():
    try:
        log_file = os.path.expanduser("~/gemini_log.json")
        if os.path.exists(log_file):
            with open(log_file) as f:
                return jsonify(json.load(f))
    except:
        pass
    return jsonify([])

@app.route('/api/control', methods=['POST'])
def api_control():
    cmd = request.get_json().get('action')
    if cmd == 'start':
        running, _ = is_speaker_running()
        if running: return jsonify({"message":"すでに起動中です"})
        subprocess.run(["amixer", "-c", "2", "sset", "PCM", "100%"])
        subprocess.Popen(["python3", os.path.expanduser("~/smart_speaker.py")],
            stdout=open(os.path.expanduser("~/speaker.log"),"a"), stderr=subprocess.STDOUT)
        return jsonify({"message":"起動しました ▶"})
    elif cmd == 'stop':
        running, pid = is_speaker_running()
        if not running: return jsonify({"message":"すでに停止中です"})
        subprocess.run(["kill", str(pid)])
        return jsonify({"message":"停止しました ⏹"})
    elif cmd == 'restart':
        running, pid = is_speaker_running()
        if running: subprocess.run(["kill", str(pid)]); time.sleep(1)
        subprocess.run(["amixer", "-c", "2", "sset", "PCM", "100%"])
        subprocess.Popen(["python3", os.path.expanduser("~/smart_speaker.py")],
            stdout=open(os.path.expanduser("~/speaker.log"),"a"), stderr=subprocess.STDOUT)
        return jsonify({"message":"再起動しました 🔄"})
    elif cmd == 'reboot':
        def do_reboot(): time.sleep(1); subprocess.run(["sudo","reboot"])
        threading.Thread(target=do_reboot).start()
        return jsonify({"message":"本体を再起動します ⚡"})
    return jsonify({"message":"不明なコマンド"})

if __name__ == '__main__':
    print("=== ジェミニパイ ダッシュボード ===")
    print("スマホブラウザで → http://gemini-pi.local:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
