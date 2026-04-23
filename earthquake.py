import json
import threading
import time
import subprocess
import os
import tempfile
import websocket
from gtts import gTTS
from config import AUDIO_DEVICE, TEMPO, LOCATION_NAME, PREFECTURE, MIN_INTENSITY
import oled_display as oled

TARGET_PREF  = PREFECTURE
  # 震度2以上

INTENSITY_ORDER = {"0":0,"1":1,"2":2,"3":3,"4":4,"5-":5,"5+":6,"6-":7,"6+":8,"7":9}

def intensity_to_text(val):
    table = {
        "0":"0","1":"1","2":"2","3":"3","4":"4",
        "5-":"5弱","5+":"5強","6-":"6弱","6+":"6強","7":"7"
    }
    return table.get(str(val), str(val))

def intensity_value(val):
    return INTENSITY_ORDER.get(str(val), 0)

def speak_alert(text):
    print(f"[地震速報]: {text}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        mp3_path = f.name
    wav_path = mp3_path.replace(".mp3", ".wav")
    try:
        tts = gTTS(text, lang="ja")
        tts.save(mp3_path)
        subprocess.run(["sox", mp3_path, wav_path, "tempo", "1.1"],
                       check=True, stderr=subprocess.DEVNULL)
        subprocess.run(["aplay", "-D", AUDIO_DEVICE, wav_path],
                       stderr=subprocess.DEVNULL)
    finally:
        if os.path.exists(mp3_path): os.remove(mp3_path)
        if os.path.exists(wav_path): os.remove(wav_path)

def get_fukuoka_intensity(points):
    """福岡県内の観測点から最大震度を取得"""
    max_val = -1
    max_text = None
    for point in points:
        if TARGET_PREF in point.get("pref", ""):
            v = intensity_value(point.get("intensity", "0"))
            if v > max_val:
                max_val = v
                max_text = point.get("intensity", "0")
    return max_val, max_text

def on_message(ws, message):
    try:
        data = json.loads(message)
        code = data.get("code", 0)

        # 緊急地震速報（警報）: code=556
        if code == 556:
            body  = data.get("body", {})
            eq    = body.get("earthquake", {})
            hypo  = eq.get("hypocenter", {})
            name      = hypo.get("name", "不明")
            magnitude = eq.get("magnitude", {}).get("value", "不明")

            # 福岡県の予測震度を確認
            areas = body.get("intensity", {}).get("regions", [])
            fukuoka_val, fukuoka_int = get_fukuoka_intensity(areas)

            # 福岡県の予測震度が2以上のみ
            if fukuoka_val < MIN_INTENSITY:
                print(f"[地震速報] 福岡県の予測震度が低いためスキップ（{fukuoka_int}）")
                return

            msg = (f"緊急地震速報！震源は{name}、"
                   f"マグニチュード{magnitude}、"
                   f"福岡県での予測震度は{intensity_to_text(fukuoka_int)}です。"
                   f"すぐに身を守る行動をとってください！")
            oled.set_earthquake(msg)
            speak_alert(msg)

        # 地震情報（発生後）: code=551
        elif code == 551:
            body  = data.get("body", {})
            eq    = body.get("earthquake", {})
            hypo  = eq.get("hypocenter", {})
            name      = hypo.get("name", "不明")
            magnitude = eq.get("magnitude", {}).get("value", "不明")

            # 福岡県の観測震度を確認
            points = body.get("intensity", {}).get("points", [])
            fukuoka_val, fukuoka_int = get_fukuoka_intensity(points)

            # 福岡県の震度が2以上のみ
            if fukuoka_val < MIN_INTENSITY:
                print(f"[地震情報] 福岡県の震度が低いためスキップ（{fukuoka_int}）")
                return

            domestic_tsunami = body.get("domesticTsunami", "なし")
            tsunami_msg = ""
            if domestic_tsunami not in ["なし", "調査中", None]:
                tsunami_msg = "津波に注意してください。"

            msg = (f"地震情報です。{name}でマグニチュード{magnitude}の地震が発生しました。"
                   f"福岡県の震度は{intensity_to_text(fukuoka_int)}です。{tsunami_msg}")
            oled.set_earthquake(msg)
            speak_alert(msg)

    except Exception as e:
        print(f"[地震速報エラー] {e}")

def on_error(ws, error):
    print(f"[WebSocketエラー] {error}")

def on_close(ws, close_status_code, close_msg):
    print("[WebSocket切断] 5秒後に再接続します...")

def on_open(ws):
    print(f"[地震速報] 監視中（{TARGET_PREF}・震度{MIN_INTENSITY}以上）")

def start_earthquake_monitor():
    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://api.p2pquake.net/v2/ws",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            print(f"[地震速報接続エラー] {e}")
        print("[地震速報] 5秒後に再接続...")
        time.sleep(5)

if __name__ == "__main__":
    print("=== 地震速報モニター起動 ===")
    start_earthquake_monitor()
