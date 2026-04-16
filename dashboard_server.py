from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import subprocess, os, json, psutil, threading, time
from datetime import datetime

app = Flask(__name__)
CORS(app)

def get_system_info():
    try:
        temp_raw = subprocess.check_output(["vcgencmd", "measure_temp"]).decode().strip()
        temp_val = float(temp_raw.replace("temp=", "").replace("'C", ""))
    except:
        temp_val = 0
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    return {
        "temp": f"{temp_val:.1f}C",
        "temp_val": temp_val,
        "cpu": cpu,
        "mem_used": mem.used // 1024 // 1024,
        "mem_total": mem.total // 1024 // 1024,
        "mem_percent": mem.percent
    }

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
:root{--bg:#030d1a;--surface:#071828;--border:#0d3455;--blue:#4dc8ff;--green:#00e5a0;--orange:#ffaa44;--red:#ff4466;--text:#c8e8ff;--muted:#3a6080}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{background:var(--bg);color:var(--text);font-family:'Noto Sans JP',sans-serif;padding:16px 14px 36px;max-width:480px;margin:0 auto}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 10% 10%,rgba(0,80,200,.06) 0%,transparent 60%),radial-gradient(ellipse at 90% 90%,rgba(0,180,120,.04) 0%,transparent 60%);pointer-events:none}
.hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border)}
.logo{font-family:'Orbitron',monospace;font-size:17px;font-weight:900;color:var(--blue);letter-spacing:.12em}
.logo span{color:var(--green)}
.upd{font-size:9px;color:var(--muted);font-family:'Orbitron',monospace}
.card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:14px;margin-bottom:12px;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--blue),var(--green))}
.status-row{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.dot{width:12px;height:12px;border-radius:50%;flex-shrink:0}
.online{background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 2s infinite}
.offline{background:var(--red);box-shadow:0 0 8px var(--red)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.slabel{font-family:'Orbitron',monospace;font-size:13px;font-weight:700}
.ssub{font-size:10px;color:var(--muted);margin-top:2px}
.gauges{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.gauge-box{background:#040f1e;border:1px solid var(--border);border-radius:10px;padding:10px 8px;display:flex;flex-direction:column;align-items:center;gap:6px}
.gauge-title{font-size:9px;color:var(--muted);letter-spacing:.05em;font-family:'Orbitron',monospace}
.arc-wrap{position:relative;width:72px;height:40px}
.arc-wrap svg{width:72px;height:40px}
.arc-val{position:absolute;bottom:0;left:50%;transform:translateX(-50%);font-family:'Orbitron',monospace;font-size:12px;font-weight:700;white-space:nowrap}
.bar-wrap{width:100%;display:flex;flex-direction:column;gap:3px}
.bar-track{width:100%;height:6px;background:#0a1f35;border-radius:3px;overflow:hidden}
.bar-fill{height:100%;border-radius:3px;transition:width .6s ease}
.bar-nums{display:flex;justify-content:space-between;font-size:9px;color:var(--muted);font-family:'Orbitron',monospace}
.sec{font-family:'Orbitron',monospace;font-size:9px;color:var(--muted);letter-spacing:.2em;margin-bottom:8px}
.btn-row{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.btn{padding:8px 14px;border:1px solid;border-radius:8px;font-family:'Orbitron',monospace;font-size:10px;font-weight:700;cursor:pointer;background:var(--surface);display:flex;align-items:center;gap:5px;transition:opacity .15s;white-space:nowrap}
.btn:active{opacity:.65}
.ico{font-size:13px}
.g{border-color:var(--green);color:var(--green)}
.r{border-color:var(--red);color:var(--red)}
.o{border-color:var(--orange);color:var(--orange)}
.b{border-color:var(--blue);color:var(--blue)}
.logcard{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:14px}
.logcard::before{content:'';display:block;height:2px;background:linear-gradient(90deg,var(--orange),var(--blue));border-radius:1px;margin-bottom:12px}
.logitem{padding:9px 0;border-bottom:1px solid var(--border)}
.logitem:last-child{border-bottom:none}
.logq{font-size:11px;color:var(--blue);margin-bottom:3px}
.loga{font-size:10px;color:var(--muted);line-height:1.5}
.logt{font-size:8px;color:#1a3a50;margin-top:3px;font-family:'Orbitron',monospace}
.empty{font-size:11px;color:var(--muted);text-align:center;padding:16px}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);background:#0d2a45;border:1px solid var(--blue);color:var(--blue);padding:10px 22px;border-radius:100px;font-size:12px;font-family:'Orbitron',monospace;transition:transform .3s;white-space:nowrap;z-index:999}
.toast.show{transform:translateX(-50%) translateY(0)}
</style>
</head>
<body>
<div class="hdr">
  <div><div class="logo">GEMINI<span>PI</span></div><div class="upd" id="upd">更新中...</div></div>
  <div style="font-size:24px">🤖</div>
</div>
<div class="card">
  <div class="status-row">
    <div class="dot" id="dot"></div>
    <div><div class="slabel" id="stxt">確認中...</div><div class="ssub" id="ssub"></div></div>
  </div>
  <div class="gauges">
    <div class="gauge-box">
      <div class="gauge-title">温度</div>
      <div class="arc-wrap">
        <svg viewBox="0 0 72 40">
          <path d="M8 38 A 28 28 0 0 1 64 38" fill="none" stroke="#0a1f35" stroke-width="7" stroke-linecap="round"/>
          <path id="arc-temp" d="M8 38 A 28 28 0 0 1 64 38" fill="none" stroke="#00e5a0" stroke-width="7" stroke-linecap="round" stroke-dasharray="88" stroke-dashoffset="88" style="transition:stroke-dashoffset .6s,stroke .4s"/>
        </svg>
        <div class="arc-val" id="val-temp" style="color:#00e5a0">--</div>
      </div>
    </div>
    <div class="gauge-box">
      <div class="gauge-title">CPU</div>
      <div class="arc-wrap">
        <svg viewBox="0 0 72 40">
          <path d="M8 38 A 28 28 0 0 1 64 38" fill="none" stroke="#0a1f35" stroke-width="7" stroke-linecap="round"/>
          <path id="arc-cpu" d="M8 38 A 28 28 0 0 1 64 38" fill="none" stroke="#00e5a0" stroke-width="7" stroke-linecap="round" stroke-dasharray="88" stroke-dashoffset="88" style="transition:stroke-dashoffset .6s,stroke .4s"/>
        </svg>
        <div class="arc-val" id="val-cpu" style="color:#00e5a0">--</div>
      </div>
    </div>
    <div class="gauge-box">
      <div class="gauge-title">メモリ</div>
      <div class="bar-wrap">
        <div class="bar-track"><div class="bar-fill" id="bar-mem" style="width:0%;background:#00e5a0"></div></div>
        <div class="bar-nums"><span id="mem-used">--</span><span id="mem-total">--</span></div>
        <div style="font-family:'Orbitron',monospace;font-size:14px;font-weight:700;text-align:center;margin-top:2px;color:#00e5a0" id="val-mem">--%</div>
      </div>
    </div>
  </div>
</div>
<div class="sec">CONTROLS</div>
<div class="btn-row">
  <button class="btn g" onclick="act('start')"><span class="ico">▶</span>起動</button>
  <button class="btn r" onclick="act('stop')"><span class="ico">⏹</span>停止</button>
  <button class="btn o" onclick="act('restart')"><span class="ico">🔄</span>再起動</button>
  <button class="btn b" onclick="doReboot()"><span class="ico">⚡</span>本体再起動</button>
</div>
<div class="logcard">
  <div class="sec" style="margin-bottom:0">RECENT CONVERSATIONS</div>
  <div id="logs"><div class="empty">まだ会話がありません</div></div>
</div>
<div class="toast" id="toast"></div>
<script>
const BASE=window.location.origin;
const ARC=88;
function setArc(id,valId,pct,label){
  const arc=document.getElementById(id);
  const el=document.getElementById(valId);
  arc.style.strokeDashoffset=ARC-(ARC*Math.min(pct,100)/100);
  el.textContent=label;
  const c=pct>80?'#ff4466':pct>60?'#ffaa44':'#00e5a0';
  arc.style.stroke=c; el.style.color=c;
}
function setBar(pct,used,total){
  const bar=document.getElementById('bar-mem');
  const c=pct>80?'#ff4466':pct>60?'#ffaa44':'#00e5a0';
  bar.style.width=pct+'%'; bar.style.background=c;
  document.getElementById('mem-used').textContent=used+'M';
  document.getElementById('mem-total').textContent=total+'M';
  const el=document.getElementById('val-mem');
  el.textContent=Math.round(pct)+'%'; el.style.color=c;
}
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2500)}
async function fetchStatus(){
  try{
    const r=await fetch(BASE+'/api/status');
    const d=await r.json();
    const dot=document.getElementById('dot');
    dot.className='dot '+(d.running?'online':'offline');
    document.getElementById('stxt').textContent=d.running?'稼働中':'停止中';
    document.getElementById('stxt').style.color=d.running?'#00e5a0':'#ff4466';
    document.getElementById('ssub').textContent=d.running?'PID: '+d.pid:'起動ボタンで再開できます';
    const s=d.system;
    setArc('arc-temp','val-temp',s.temp_val/85*100,s.temp_val.toFixed(1)+'℃');
    setArc('arc-cpu','val-cpu',s.cpu,s.cpu.toFixed(0)+'%');
    setBar(s.mem_percent,s.mem_used,s.mem_total);
    document.getElementById('upd').textContent='最終更新: '+new Date().toLocaleTimeString('ja-JP');
  }catch(e){document.getElementById('stxt').textContent='接続エラー';}
}
async function fetchLog(){
  try{
    const r=await fetch(BASE+'/api/log');
    const logs=await r.json();
    const el=document.getElementById('logs');
    if(!logs.length){el.innerHTML='<div class="empty">まだ会話がありません</div>';return;}
    el.innerHTML=logs.slice(-5).reverse().map(l=>`
      <div class="logitem">
        <div class="logq">Q: ${l.question}</div>
        <div class="loga">${l.answer.substring(0,90)}${l.answer.length>90?'...':''}</div>
        <div class="logt">${l.time}</div>
      </div>`).join('');
  }catch(e){}
}
async function act(cmd){
  toast({start:'起動中...',stop:'停止中...',restart:'再起動中...'}[cmd]||'処理中...');
  try{
    const r=await fetch(BASE+'/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:cmd})});
    const d=await r.json(); toast(d.message);
    setTimeout(fetchStatus,2000);
  }catch(e){toast('エラーが発生しました');}
}
function doReboot(){if(confirm('ラズパイ本体を再起動しますか？'))act('reboot');}
fetchStatus();fetchLog();
setInterval(fetchStatus,10000);setInterval(fetchLog,15000);
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
