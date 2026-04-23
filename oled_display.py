import time
import threading
import math
from datetime import datetime
import urllib.request
import json
import os
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

try:
    from config import LATITUDE, LONGITUDE, OWM_API_KEY, POLLEN_API_KEY
except:
    LATITUDE, LONGITUDE = 33.73, 130.47
    OWM_API_KEY = ""
    POLLEN_API_KEY = ""

serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)
W, H = 128, 64

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
try:
    font_time  = ImageFont.truetype(FONT_PATH, 13)
    font_mid   = ImageFont.truetype(FONT_PATH, 10)
    font_small = ImageFont.truetype(FONT_PATH, 9)
except:
    font_time  = ImageFont.load_default()
    font_mid   = font_time
    font_small = font_time

WEATHER_MAP = {
    0:"快晴",1:"晴れ",2:"一部曇",3:"曇り",
    45:"霧",48:"霧",51:"小雨",53:"雨",55:"大雨",
    61:"小雨",63:"雨",65:"大雨",71:"小雪",73:"雪",75:"大雪",
    80:"にわか雨",81:"雨",82:"大雨",95:"雷雨",96:"雷雨",99:"雷雨"
}

state = {
    "mode": "standby",
    "question": "",
    "answer": "",
    "scroll_pos": 0,
    "weather": None,
    "eq_msg": "",
    "eq_start": 0,
}
state_lock = threading.Lock()
angle = 0.0
tape_wobble = 0.0

def fetch_weather():
    try:
        url = (f"https://api.open-meteo.com/v1/forecast"
               f"?latitude={LATITUDE}&longitude={LONGITUDE}"
               f"&current=temperature_2m,weathercode,windspeed_10m,relative_humidity_2m"
               f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode"
               f"&timezone=Asia%2FTokyo&forecast_days=2")
        with urllib.request.urlopen(url, timeout=8) as r:
            d = json.loads(r.read())
        current = d["current"]
        daily   = d["daily"]
        pm25_level = "---"
        try:
            pm_url = (f"http://api.openweathermap.org/data/2.5/air_pollution"
                      f"?lat={LATITUDE}&lon={LONGITUDE}&appid={OWM_API_KEY}")
            with urllib.request.urlopen(pm_url, timeout=5) as r:
                pm = json.loads(r.read())
            pm25 = pm["list"][0]["components"]["pm2_5"]
            pm25_level = "良好" if pm25<12 else "普通" if pm25<35 else "悪い" if pm25<55 else "危険"
        except:
            pass
        pollen_str = "---"
        try:
            p_url = (f"https://pollen.googleapis.com/v1/forecast:lookup"
                     f"?location.longitude={LONGITUDE}&location.latitude={LATITUDE}&days=1&key={POLLEN_API_KEY}")
            with urllib.request.urlopen(p_url, timeout=5) as r:
                pd = json.loads(r.read())
            cat_map  = {"None":"なし","Very Low":"極少","Low":"少","Medium":"中","High":"多","Very High":"激多"}
            code_map = {"JAPANESE_CEDAR":"スギ","JAPANESE_CYPRESS":"ヒノキ","GRAMINALES":"イネ科"}
            items = []
            for plant in pd["dailyInfo"][0]["plantInfo"]:
                if plant.get("inSeason") or plant["indexInfo"]["value"] >= 2:
                    name = code_map.get(plant["code"], "")
                    lv   = cat_map.get(plant["indexInfo"]["category"], "")
                    items.append(f"{name}:{lv}")
            pollen_str = " ".join(items) if items else "なし"
        except:
            pass
        w = lambda c: WEATHER_MAP.get(c, "不明")
        return {
            "temp":        current["temperature_2m"],
            "weather":     w(current["weathercode"]),
            "humidity":    current["relative_humidity_2m"],
            "wind":        current["windspeed_10m"],
            "pm25":        pm25_level,
            "pollen":      pollen_str,
            "tom_weather": w(daily["weathercode"][1]),
            "tom_max":     daily["temperature_2m_max"][1],
            "tom_min":     daily["temperature_2m_min"][1],
            "tom_rain":    daily["precipitation_probability_max"][1],
        }
    except Exception as e:
        print(f"[OLED天気] {e}")
        return None

def weather_updater():
    while True:
        w = fetch_weather()
        with state_lock:
            if w:
                state["weather"] = w
        time.sleep(3 * 60 * 60)

def bezier(p0, p1, p2, steps=30):
    pts = []
    for i in range(steps+1):
        t = i / steps
        x = (1-t)**2*p0[0] + 2*(1-t)*t*p1[0] + t**2*p2[0]
        y = (1-t)**2*p0[1] + 2*(1-t)*t*p1[1] + t**2*p2[1]
        pts.append((int(x), int(y)))
    return pts

def draw_bezier(draw, pts, fill="white", width=1):
    for i in range(len(pts)-1):
        draw.line([pts[i], pts[i+1]], fill=fill, width=width)

def draw_cassette_base(draw, ang, wobble):
    # 黄色エリア: 時計
    time_str = datetime.now().strftime("%H:%M")
    bbox = draw.textbbox((0,0), time_str, font=font_time)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) // 2
    draw.text((tx, 0), time_str, font=font_time, fill="white")
    draw.line([(0,14),(W,14)], fill="white", width=1)

    # 青エリア
    draw.rounded_rectangle([(1,15),(W-2,H-2)], radius=3, fill="black", outline="white", width=1)

    # テープ窓
    win_x1, win_x2 = 28, 100
    win_y1, win_y2 = 18, 61
    draw.rounded_rectangle([(win_x1,win_y1),(win_x2,win_y2)],
                           radius=3, fill="black", outline="white", width=1)

    tape_cx = (win_x1 + win_x2) / 2
    mid_y   = (win_y1 + win_y2) / 2
    neck_w  = 10.0
    w_off   = math.sin(wobble * 8) * 1.2

    # 上の水平ライン
    draw.line([(win_x1+1, win_y1+2),(win_x2-1, win_y1+2)], fill="white", width=1)
    # 下の水平ライン
    draw.line([(win_x1+1, win_y2-2),(win_x2-1, win_y2-2)], fill="white", width=1)

    # 左の曲線（外側に膨らむ）
    pts = bezier(
        (win_x1, win_y1+2),
        (win_x1 - 8, mid_y + w_off),
        (win_x1, win_y2-2),
    )
    draw_bezier(draw, pts)

    # 右の曲線（外側に膨らむ）
    pts = bezier(
        (win_x2, win_y1+2),
        (win_x2 + 8, mid_y - w_off),
        (win_x2, win_y2-2),
    )
    draw_bezier(draw, pts)

    # くびれ左
    pts = bezier(
        (win_x1+1, win_y1+2),
        (tape_cx - neck_w + w_off, mid_y),
        (win_x1+1, win_y2-2),
    )
    draw_bezier(draw, pts)

    # くびれ右
    pts = bezier(
        (win_x2-1, win_y1+2),
        (tape_cx + neck_w - w_off, mid_y),
        (win_x2-1, win_y2-2),
    )
    draw_bezier(draw, pts)

    # リール
    reel_r = 20
    hub_r  = 6
    hole_r = 2
    reel_cy = int(mid_y)
    left_rx  = 6
    right_rx = W - 6

    for rx in [left_rx, right_rx]:
        draw.ellipse([(rx-reel_r,reel_cy-reel_r),(rx+reel_r,reel_cy+reel_r)],
                    outline="white", width=1)
        draw.ellipse([(rx-hub_r,reel_cy-hub_r),(rx+hub_r,reel_cy+hub_r)],
                    fill="white")
        draw.ellipse([(rx-hole_r,reel_cy-hole_r),(rx+hole_r,reel_cy+hole_r)],
                    fill="black")
        for i in range(5):
            a  = ang + (i / 5) * math.pi * 2
            x1 = rx + int(math.cos(a) * (hole_r+1))
            y1 = reel_cy + int(math.sin(a) * (hole_r+1))
            x2 = rx + int(math.cos(a) * (hub_r-1))
            y2 = reel_cy + int(math.sin(a) * (hub_r-1))
            draw.line([(x1,y1),(x2,y2)], fill="black", width=1)
        for i in range(18):
            a1 = ang + (i / 18) * math.pi * 2
            a2 = ang + ((i+0.5) / 18) * math.pi * 2
            r_in  = reel_r - 3
            r_out = reel_r
            pts2 = [
                (rx+int(math.cos(a1)*r_in),  reel_cy+int(math.sin(a1)*r_in)),
                (rx+int(math.cos(a1)*r_out), reel_cy+int(math.sin(a1)*r_out)),
                (rx+int(math.cos(a2)*r_out), reel_cy+int(math.sin(a2)*r_out)),
                (rx+int(math.cos(a2)*r_in),  reel_cy+int(math.sin(a2)*r_in)),
            ]
            draw.polygon(pts2, fill="white", outline="black")

def draw_listening(draw, question, ang, wobble):
    draw_cassette_base(draw, ang, wobble)
    win_x1, win_x2 = 30, 98
    win_y1, win_y2 = 20, 60
    base_y = (win_y1 + win_y2) // 2
    count  = 16
    for i in range(count):
        x = win_x1 + i * ((win_x2-win_x1) // count) + 2
        h = int(abs(math.sin(ang + i * 0.5)) * 14) + 2
        draw.rectangle([(x, base_y-h),(x+2, base_y+h)], fill="white")

def draw_thinking(draw, ang, wobble):
    draw_cassette_base(draw, ang, wobble)
    dots = "." * ((int(time.time() * 2) % 3) + 1)
    draw.text((38, 33), f"AI{dots}", font=font_small, fill="black")

def draw_speaking(draw, answer, scroll_pos, ang, wobble):
    draw_cassette_base(draw, ang, wobble)
    cpl = 10
    lines = [answer[i:i+cpl] for i in range(0, len(answer), cpl)]
    for idx, line in enumerate(lines[scroll_pos:scroll_pos+3]):
        draw.text((32, 22 + idx * 12), line, font=font_small, fill="white")

def draw_weather_display(draw, w):
    if not w:
        draw.text((2,20), "取得中...", font=font_mid, fill="white")
        return
    draw.text((2, 1), "Tomorrow", font=font_small, fill="white")
    draw.line([(0,12),(W,12)], fill="white", width=1)
    cx, cy = 32, 36
    weather = w.get("tom_weather","")
    if "晴" in weather:
        draw.ellipse([(cx-8,cy-8),(cx+8,cy+8)], outline="white", width=1)
        for i in range(8):
            a  = i * math.pi / 4
            x1 = cx + int(math.cos(a)*10)
            y1 = cy + int(math.sin(a)*10)
            x2 = cx + int(math.cos(a)*13)
            y2 = cy + int(math.sin(a)*13)
            draw.line([(x1,y1),(x2,y2)], fill="white", width=1)
    elif "雨" in weather:
        draw.ellipse([(cx-9,cy-6),(cx+9,cy+4)], outline="white", width=1)
        for i in range(5):
            rx2 = cx - 8 + i * 4
            draw.line([(rx2,cy+7),(rx2-2,cy+12)], fill="white", width=1)
    else:
        draw.ellipse([(cx-10,cy-4),(cx+10,cy+6)], outline="white", width=1)
        draw.ellipse([(cx-6,cy-8),(cx+6,cy+0)], outline="white", width=1)
    draw.text((52, 18), f"{w['tom_max']:.0f}/{w['tom_min']:.0f}C", font=font_small, fill="white")
    draw.text((52, 30), f"Rain:{w['tom_rain']}%",                  font=font_small, fill="white")
    draw.text((52, 42), f"PM2.5:{w['pm25']}",                      font=font_small, fill="white")
    draw.text((2,  54), w['pollen'],                                font=font_small, fill="white")

def draw_earthquake(draw, msg, flash):
    if flash:
        draw.rectangle([(0,0),(W,H)], fill="white")
        fg = "black"
    else:
        draw.rectangle([(0,0),(W,H)], fill="black")
        fg = "white"
    draw.text((4,  2), "!! EARTHQUAKE !!", font=font_small, fill=fg)
    draw.line([(0,13),(W,13)], fill=fg, width=1)
    draw.text((2, 16), msg[:16],                                    font=font_small, fill=fg)
    draw.text((2, 28), msg[16:32] if len(msg)>16 else "",           font=font_small, fill=fg)
    draw.text((2, 40), msg[32:48] if len(msg)>32 else "",           font=font_small, fill=fg)

# ======== 外部API ========
def set_listening(question=""):
    with state_lock:
        state["mode"] = "listening"
        state["question"] = question

def set_thinking():
    with state_lock:
        state["mode"] = "thinking"

def set_speaking(answer):
    with state_lock:
        state["mode"] = "speaking"
        state["answer"] = answer
        state["scroll_pos"] = 0

def set_standby():
    with state_lock:
        if state["mode"] not in ["earthquake"]:
            state["mode"] = "standby"

def set_earthquake(msg):
    with state_lock:
        state["mode"] = "earthquake"
        state["eq_msg"] = msg
        state["eq_start"] = time.time()

def set_weather():
    with state_lock:
        state["mode"] = "weather"

# ======== メインループ ========
def display_loop():
    global angle, tape_wobble
    scroll_timer = 0
    while True:
        with state_lock:
            mode     = state["mode"]
            q        = state["question"]
            ans      = state["answer"]
            sp       = state["scroll_pos"]
            w        = state["weather"]
            eq_msg   = state["eq_msg"]
            eq_start = state["eq_start"]

        try:
            with canvas(device) as draw:
                if mode == "standby":
                    draw_cassette_base(draw, angle, tape_wobble)
                    angle       += 0.03
                    tape_wobble += 0.05

                elif mode == "listening":
                    draw_listening(draw, q, angle, tape_wobble)
                    angle       += 0.12
                    tape_wobble += 0.1

                elif mode == "thinking":
                    draw_thinking(draw, angle, tape_wobble)
                    angle       += 0.02
                    tape_wobble += 0.03

                elif mode == "speaking":
                    draw_speaking(draw, ans, sp, angle, tape_wobble)
                    angle       += 0.04
                    tape_wobble += 0.05
                    scroll_timer += 1
                    if scroll_timer >= 8:
                        scroll_timer = 0
                        cpl = 10
                        total = (len(ans) + cpl - 1) // cpl
                        with state_lock:
                            if state["scroll_pos"] + 3 < total:
                                state["scroll_pos"] += 1

                elif mode == "weather":
                    draw_weather_display(draw, w)

                elif mode == "earthquake":
                    elapsed = time.time() - eq_start
                    if elapsed > 15:
                        with state_lock:
                            state["mode"] = "standby"
                    else:
                        flash = int(time.time() * 3) % 2 == 0
                        draw_earthquake(draw, eq_msg, flash)

        except Exception as e:
            print(f"[OLED描画エラー] {e}")

        time.sleep(0.1)

def start_oled():
    threading.Thread(target=weather_updater, daemon=True).start()
    threading.Thread(target=display_loop,    daemon=True).start()
    print("[OLED] 起動完了")

if __name__ == "__main__":
    print("[OLED] テスト起動")
    start_oled()
    time.sleep(60)
