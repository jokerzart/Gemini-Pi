# ============================================================
# GeminiPi 設定ファイル / Configuration File
# ============================================================
# このファイルをコピーして config.py を作成してください
# Copy this file and rename it to config.py
#
#   cp config_sample.py config.py
#   nano config.py
#
# ⚠️  config.py は .gitignore で除外されています
# ⚠️  config.py is excluded from git via .gitignore
# ============================================================

# ── Gemini API ───────────────────────────────────────────────
# Google AI Studio で取得 / Get from Google AI Studio
# https://aistudio.google.com/app/apikey
GEMINI_API_KEY  = "your_gemini_api_key_here"

# ── OpenWeatherMap API（PM2.5取得）───────────────────────────
# 無料登録で取得 / Free registration required
# https://openweathermap.org/api
OWM_API_KEY     = "your_openweathermap_api_key_here"

# ── Google Pollen API（花粉情報）─────────────────────────────
# Google Cloud Console で有効化 / Enable in Google Cloud Console
# https://console.cloud.google.com
POLLEN_API_KEY  = "your_google_pollen_api_key_here"

# ── 場所設定 / Location Settings ────────────────────────────
# 緯度・経度は Google Maps で確認できます
# You can find latitude/longitude on Google Maps
LATITUDE        = 33.73          # 緯度 / Latitude
LONGITUDE       = 130.47         # 経度 / Longitude
LOCATION_NAME   = "福岡県古賀市"  # 場所の名前 / Location name
PREFECTURE      = "福岡県"        # 都道府県（地震速報フィルター用）
CITY_NAME       = "古賀市"        # 市区町村名

# ── 音声設定 / Audio Settings ───────────────────────────────
# USBデバイスの番号は以下で確認 / Check USB device number with:
#   arecord -l
AUDIO_DEVICE    = "plughw:2,0"   # 例: plughw:カード番号,デバイス番号
TEMPO           = "1.4"          # 読み上げ速度 / Speech speed
                                 # 1.0=普通 / 1.4=少し速め / 2.0=かなり速め

# ── 朝の天気アナウンス / Morning Weather Announcement ────────
MORNING_HOUR    = 7              # 時 / Hour (24h)
MORNING_MINUTE  = 30             # 分 / Minute

# ── 地震速報設定 / Earthquake Alert Settings ─────────────────
MIN_INTENSITY   = 2              # 読み上げる最小震度 / Minimum intensity to announce
                                 # 1=震度1以上 / 2=震度2以上（推奨）/ 3=震度3以上
