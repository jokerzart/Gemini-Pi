import speech_recognition as sr
from gtts import gTTS
from datetime import date, datetime, timedelta
from google import genai
import urllib.request, json
import subprocess, os, tempfile, threading, time
from config import (
    GEMINI_API_KEY, OWM_API_KEY, POLLEN_API_KEY,
    LATITUDE, LONGITUDE, LOCATION_NAME,
    AUDIO_DEVICE, TEMPO, MORNING_HOUR, MORNING_MINUTE
)

WAKE_WORDS   = ["Ok Google", "OK Google", "OKグーグル", "okグーグル", "オーケーグーグル", "オッケーグーグル", "ok google"]
CANCEL_WORDS = ["キャンセル", "やめて", "ストップ", "止めて"]
LOG_FILE     = os.path.expanduser("~/gemini_log.json")

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """あなたはジェミニというアシスタントです。
以下のルールを必ず守って答えてください：
1. 最初に必ず「はい！」と返事をする
2. 結論・答えを最初に端的に述べる
3. その後に理由や補足を話す
4. 余計な前置きや回りくどい表現は使わない
5. 音声で読み上げるので、箇条書きや記号は使わない
6. 回答は簡潔に、通常の7割程度の文章量に抑える
7. 回答の最後に「ちなみに、」で始まる一言豆知識を必ず付け加える"""

WEATHER_SYSTEM_PROMPT = """あなたはジェミニというアシスタントです。
以下のルールを必ず守って答えてください：
1. 最初に必ず「はい！」と返事をする
2. 結論・答えを最初に端的に述べる
3. 天気・気温・降水確率・PM2.5・花粉を全て漏れなく伝える
4. 余計な前置きや回りくどい表現は使わない
5. 音声で読み上げるので、箇条書きや記号は使わない
6. 回答の最後に今日の服装・持ち物アドバイスを必ず入れる
7. 花粉が多い場合はマスクを勧める"""

cancel_flag = threading.Event()
current_play_proc = None
play_lock = threading.Lock()

def save_log(question, answer):
    logs = []
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                logs = json.load(f)
    except:
        pass
    logs.append({
        "question": question,
        "answer": answer,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    if len(logs) > 20:
        logs = logs[-20:]
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, ensure_ascii=False)

def get_pollen():
    url = (f"https://pollen.googleapis.com/v1/forecast:lookup"
           f"?location.longitude={LONGITUDE}&location.latitude={LATITUDE}&days=1&key={POLLEN_API_KEY}")
    with urllib.request.urlopen(url) as r:
        d = json.loads(r.read())
    category_map = {
        "None":"なし","Very Low":"非常に少ない","Low":"少ない",
        "Medium":"やや多い","High":"多い","Very High":"非常に多い"
    }
    code_map = {
        "JAPANESE_CEDAR":"スギ","JAPANESE_CYPRESS":"ヒノキ","GRAMINALES":"イネ科"
    }
    results = []
    for plant in d["dailyInfo"][0]["plantInfo"]:
        name = code_map.get(plant["code"], plant["displayName"])
        cat  = category_map.get(plant["indexInfo"]["category"], plant["indexInfo"]["category"])
        val  = plant["indexInfo"]["value"]
        if plant.get("inSeason", False) or val >= 2:
            results.append(f"{name}:{cat}(指数{val})")
    return "、".join(results) if results else "花粉はほぼなし"

def get_weather():
    weather_map = {
        0:"快晴",1:"晴れ",2:"一部曇り",3:"曇り",
        45:"霧",48:"霧",51:"小雨",53:"雨",55:"大雨",
        61:"小雨",63:"雨",65:"大雨",71:"小雪",73:"雪",75:"大雪",
        80:"にわか雨",81:"雨",82:"大雨",95:"雷雨",96:"雷雨",99:"雷雨"
    }
    def w(code): return weather_map.get(code, "不明")

    url = (f"https://api.open-meteo.com/v1/forecast"
           f"?latitude={LATITUDE}&longitude={LONGITUDE}"
           f"&current=temperature_2m,weathercode,windspeed_10m,relative_humidity_2m"
           f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,precipitation_probability_max"
           f"&timezone=Asia%2FTokyo&forecast_days=3&past_days=1")
    with urllib.request.urlopen(url) as res:
        data = json.loads(res.read())

    current = data["current"]
    daily   = data["daily"]
    today_str = date.today().isoformat()
    times = daily["time"]
    today_idx     = times.index(today_str) if today_str in times else 1
    yesterday_idx = today_idx - 1

    today_max = daily["temperature_2m_max"][today_idx]
    today_min = daily["temperature_2m_min"][today_idx]
    yest_max  = daily["temperature_2m_max"][yesterday_idx]
    temp_diff = round(today_max - yest_max, 1)
    diff_str  = f"+{temp_diff}度" if temp_diff >= 0 else f"{temp_diff}度"

    result = (
        f"【現在】{w(current['weathercode'])}、気温{current['temperature_2m']}℃、"
        f"湿度{current['relative_humidity_2m']}%、風速{current['windspeed_10m']}km/h\n"
        f"【今日】{w(daily['weathercode'][today_idx])}、"
        f"最高{today_max}℃／最低{today_min}℃、"
        f"降水確率{daily['precipitation_probability_max'][today_idx]}%\n"
        f"【昨日との比較】最高気温が昨日より{diff_str}（昨日最高{yest_max}℃）\n"
        f"【明日】{w(daily['weathercode'][today_idx+1])}、"
        f"最高{daily['temperature_2m_max'][today_idx+1]}℃／最低{daily['temperature_2m_min'][today_idx+1]}℃、"
        f"降水確率{daily['precipitation_probability_max'][today_idx+1]}%\n"
        f"【明後日】{w(daily['weathercode'][today_idx+2])}、"
        f"最高{daily['temperature_2m_max'][today_idx+2]}℃／最低{daily['temperature_2m_min'][today_idx+2]}℃"
    )

    try:
        pm_url = (f"http://api.openweathermap.org/data/2.5/air_pollution"
                  f"?lat={LATITUDE}&lon={LONGITUDE}&appid={OWM_API_KEY}")
        with urllib.request.urlopen(pm_url) as res:
            pm_data = json.loads(res.read())
        pm25 = pm_data["list"][0]["components"]["pm2_5"]
        pm_comment = ("良好" if pm25 < 12 else "普通" if pm25 < 35
                      else "悪い（マスク推奨）" if pm25 < 55 else "非常に悪い（外出注意）")
        result += f"\n【PM2.5】{pm25:.1f}μg/m³（{pm_comment}）"
    except:
        result += "\n【PM2.5】取得中"

    try:
        result += f"\n【花粉】{get_pollen()}"
    except:
        result += "\n【花粉】取得中"

    return result

def ask_gemini_weather(weather_info):
    today = date.today().strftime("%Y年%m月%d日")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"今日は{today}です。\n\n【{LOCATION_NAME}の最新天気】\n{weather_info}\n\n今日の天気・花粉・PM2.5・服装アドバイスを子供がいる家庭向けにわかりやすく教えてください。",
        config={"system_instruction": WEATHER_SYSTEM_PROMPT}
    )
    return response.text

def ask_gemini(prompt):
    today = date.today().strftime("%Y年%m月%d日")
    weather_keywords = ["天気","気温","雨","晴","曇","雪","傘","予報","PM","花粉","空気","服装","長袖","半袖","コート","暑","寒","湿度","降水","マスク","外出"]
    if any(kw in prompt for kw in weather_keywords):
        try:
            return ask_gemini_weather(get_weather())
        except Exception as e:
            print(f"[天気取得失敗] {e}")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"今日は{today}です。\n\n{prompt}",
        config={"system_instruction": SYSTEM_PROMPT}
    )
    return response.text

def morning_announcement():
    while True:
        now    = datetime.now()
        target = now.replace(hour=MORNING_HOUR, minute=MORNING_MINUTE, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait_sec = (target - now).total_seconds()
        print(f"[朝の天気] 次回: {target.strftime('%Y-%m-%d %H:%M')} ({int(wait_sec)}秒後)")
        time.sleep(wait_sec)
        print("[朝の天気] 読み上げ開始")
        try:
            answer = ask_gemini_weather(get_weather())
            speak(f"おはようございます！毎朝の天気をお伝えします。{answer}")
            save_log("朝の天気（自動）", answer)
        except Exception as e:
            print(f"[朝の天気エラー] {e}")

def speak(text):
    global current_play_proc
    if cancel_flag.is_set():
        return
    print(f"[ジェミニ]: {text}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        mp3_path = f.name
    wav_path = mp3_path.replace(".mp3", ".wav")
    try:
        tts = gTTS(text, lang="ja")
        tts.save(mp3_path)
        subprocess.run(["sox", mp3_path, wav_path, "tempo", TEMPO],
                       check=True, stderr=subprocess.DEVNULL)
        with play_lock:
            current_play_proc = subprocess.Popen(
                ["aplay", "-D", AUDIO_DEVICE, wav_path],
                stderr=subprocess.DEVNULL)
        while current_play_proc and current_play_proc.poll() is None:
            if cancel_flag.is_set():
                with play_lock:
                    if current_play_proc:
                        current_play_proc.terminate()
                return
            time.sleep(0.05)
    finally:
        if os.path.exists(mp3_path): os.remove(mp3_path)
        if os.path.exists(wav_path): os.remove(wav_path)
        with play_lock:
            current_play_proc = None

def listen_once(recognizer, source, timeout=5, phrase_limit=10):
    try:
        audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        text  = recognizer.recognize_google(audio, language="ja-JP")
        print(f"[聞こえた]: {text}")
        return text
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except Exception as e:
        print(f"[エラー] {e}")
        return None

def is_cancel(text): return text and any(cw in text for cw in CANCEL_WORDS)
def is_wake(text):   return text and any(ww in text for ww in WAKE_WORDS)

def main():
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True

    print("=== スマートスピーカー起動 ===")
    print(f"毎朝{MORNING_HOUR}:{MORNING_MINUTE:02d}に天気を自動読み上げします")

    threading.Thread(target=morning_announcement, daemon=True).start()

    with sr.Microphone(device_index=1) as source:
        r.adjust_for_ambient_noise(source, duration=2)
        speak("スマートスピーカーを起動しました。オーケーグーグル、と呼びかけてください。")
        print("[待機中] ウェイクワードを待っています...")

        while True:
            cancel_flag.clear()
            text = listen_once(r, source, timeout=10, phrase_limit=6)
            if not text or is_cancel(text):
                continue
            if not is_wake(text):
                continue

            question = None
            for ww in WAKE_WORDS:
                if ww in text:
                    after = text[text.index(ww) + len(ww):].strip()
                    if len(after) > 1:
                        question = after
                    break

            cancel_flag.clear()
            speak("はい！")
            if cancel_flag.is_set():
                speak("キャンセルしました。")
                continue

            if not question:
                print("[質問待ち] どうぞ...")
                question = listen_once(r, source, timeout=7, phrase_limit=15)

            if not question:
                speak("聞き取れませんでした。もう一度呼びかけてください。")
                continue
            if is_cancel(question):
                speak("キャンセルしました。")
                continue

            print(f"[質問]: {question}")
            cancel_flag.clear()
            speak("少々お待ちください。")
            if cancel_flag.is_set():
                speak("キャンセルしました。")
                continue

            answer = [None]
            error  = [False]

            def get_answer():
                try:
                    answer[0] = ask_gemini(question)
                except Exception as e:
                    print(f"[Geminiエラー] {e}")
                    error[0] = True

            t = threading.Thread(target=get_answer, daemon=True)
            t.start()

            while t.is_alive():
                if cancel_flag.is_set():
                    break
                try:
                    audio = r.listen(source, timeout=1, phrase_time_limit=3)
                    text2 = r.recognize_google(audio, language="ja-JP")
                    print(f"[処理中]: {text2}")
                    if is_cancel(text2):
                        cancel_flag.set()
                except:
                    pass

            if cancel_flag.is_set():
                speak("キャンセルしました。")
                cancel_flag.clear()
                print("[待機中] ウェイクワードを待っています...")
                continue

            if error[0] or not answer[0]:
                speak("エラーが発生しました。もう一度お試しください。")
            else:
                save_log(question, answer[0])
                speak(answer[0])

            cancel_flag.clear()
            print("[待機中] ウェイクワードを待っています...")

if __name__ == "__main__":
    main()
