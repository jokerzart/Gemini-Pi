# 🤖 Gem-Pi — Gemini搭載AIスマートスピーカー
![Architecture](gempi.png)
![Architecture](gempiphoto.png)
**Raspberry Pi 3 × Google Gemini AI × AT-CSP1 で作る、家族のための AI スピーカー**

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-3-red)
![Gemini](https://img.shields.io/badge/Google-Gemini%202.5%20Flash-purple)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 概要 / Overview

日本で買えるスマートスピーカーって、正直まだ賢くない。
天気は教えてくれるけど、子供の「なんで？」には「wwwなんちゃらドットコムから翻訳しました...」答えられない。
ちゃんと質問に応えるGemini搭載AIスピーカー　「Gem-Pi(ジェムパイ)」
GemiPi は Raspberry Pi 3 と Google の最新 AI「Gemini 2.5 Flash」を組み合わせた、自作 AI スピーカーです。
「OK Google」と呼びかけるだけで、哲学的な質問にも、今日の花粉にも、地震速報にも答えてくれる。
市販品にはない、本物の AI 会話がここにある。

Smart speakers in Japan? Still kind of dumb, honestly.
They'll tell you the weather — but they can't handle a kid asking "why does the sky exist?"
So I built one that can.
GeminiPi pairs a Raspberry Pi 3 with Google's latest AI, Gemini 2.5 Flash.
Say "OK Google" and it handles anything — deep questions, pollen counts, earthquake alerts, morning weather.
Real AI conversation. No subscription. Built from scratch.

## システム構成図 / Architecture

👉 [インタラクティブ構成図を見る / View Interactive Architecture](https://jokerzart.github.io/Gemini-Pi/architecture.html)

![Architecture](architecture_static.svg)

## 🔌 ハードウェア接続図 / Hardware Diagram

👉 [ハードウェア接続図を見る / View Hardware Connection Diagram](https://jokerzart.github.io/Gemini-Pi/fritzing_diagram.html)

![Hardware Connection](hardware_diagram.svg)
---

## 機能 / Features

| 機能 | 説明 |
|------|------|
| 🎤 ウェイクワード検知 | 「OK Google」で起動 |
| 🌤 天気予報 | 古賀市の天気・気温・降水確率・昨日比較・3日予報 |
| 😷 PM2.5 | OpenWeatherMap API でリアルタイム取得 |
| 🌸 花粉情報 | Google Pollen API でスギ・ヒノキ・イネ科の飛散指数 |
| 👕 服装アドバイス | 子供向けに気の利いたアドバイスを自動生成 |
| ⏰ 朝の自動アナウンス | 毎朝 7:30 に天気情報を自動読み上げ |
| 🚨 地震速報 | P2P地震情報 WebSocket で福岡県・震度2以上を即座に読み上げ |
| 📱 スマホダッシュボード | ブラウザから起動・停止・再起動・ログ確認・天気・PM2.5・花粉・電圧表示 |
| 💬 会話ログ | 過去の会話をダッシュボードで確認 |
| ❌ キャンセル機能 | 「キャンセル」でいつでも中断 |

![Architecture](dashboard.png)<img src="hardware_diagram.svg" width="600"/>

---

## 必要なもの / Requirements

### ハードウェア / Hardware
- Raspberry Pi 3 Model B+
- Audio-Technica AT-CSP1（USB スピーカーフォン）
- MicroSD カード 16GB 以上
- 電源（5V / 2.5A）

### ソフトウェア / Software
- Raspberry Pi OS (Debian 13)
- Python 3.13

### API キー / API Keys
| サービス | 用途 | 料金 |
|---------|------|------|
| [Google AI Studio](https://aistudio.google.com) | Gemini API | 無料枠あり / Tier 1 後払い |
| [OpenWeatherMap](https://openweathermap.org) | PM2.5 | 無料 |
| [Google Cloud](https://console.cloud.google.com) | Pollen API | 月数円程度 |
| [P2P地震情報](https://www.p2pquake.net) | 地震速報 | 完全無料 |
| [Open-Meteo](https://open-meteo.com) | 天気予報 | 完全無料 |

---

## ファイル構成 / File Structure

```
gemini-pi/
├── smart_speaker.py      # メインプログラム（音声認識・AI応答・天気取得）
├── dashboard_server.py   # スマホダッシュボード（Flask）
├── earthquake.py         # 地震速報モニター（WebSocket）
├── start.sh              # 一発起動スクリプト
├── config_sample.py      # 設定ファイルのサンプル（APIキーはダミー）
├── .gitignore            # config.py を除外
└── README.md             # このファイル
```

> ⚠️ `config.py` は `.gitignore` で除外しています。`config_sample.py` をコピーして使ってください。

---

## セットアップ / Setup

### 1. リポジトリをクローン

```bash
git clone https://github.com/jokerzart/Gemini-Pi.git
cd Gemini-Pi
```

### 2. 必要なライブラリをインストール

```bash
pip install google-genai speechrecognition gtts flask flask-cors psutil websocket-client --break-system-packages
sudo apt install sox libsox-fmt-mp3 python3-pyaudio -y
```

### 3. 設定ファイルを作成

```bash
cp config_sample.py config.py
nano config.py
```

以下を自分の環境に合わせて編集：

```python
GEMINI_API_KEY  = "your_gemini_api_key"
OWM_API_KEY     = "your_openweathermap_key"
POLLEN_API_KEY  = "your_google_pollen_key"

LATITUDE        = 33.73       # 緯度
LONGITUDE       = 130.47      # 経度
LOCATION_NAME   = "福岡県古賀市"
PREFECTURE      = "福岡県"

AUDIO_DEVICE    = "plughw:2,0"  # arecord -l で確認
TEMPO           = "1.4"          # 読み上げ速度

MORNING_HOUR    = 7
MORNING_MINUTE  = 30

MIN_INTENSITY   = 2  # 地震速報の最小震度
```

### 4. 起動

```bash
chmod +x start.sh
./start.sh
```

### 5. ダッシュボードにアクセス

スマホのブラウザで：
```
http://gemini-pi.local:5000
```

---

## 使い方 / Usage

```
「OK Google、今日の天気は？」
→ 天気・気温・降水確率・PM2.5・花粉・服装アドバイスを読み上げ

「OK Google、安納芋って何？」
→ Gemini AI が答えてくれる（最後に豆知識も！）

「キャンセル」
→ 読み上げをいつでも中断
```

毎朝 7:30 には自動で天気情報を読み上げます。

---

## ダッシュボード / Dashboard

スマホブラウザから以下が操作できます：

- 🟢 稼働状態の確認
- 🌡 CPU温度・使用率・メモリのリアルタイム表示
- ▶️ 起動 / ⏹ 停止 / 🔄 再起動 / ⚡ 本体再起動
- 💬 直近の会話ログ

iPhoneの場合、Safari で開いて「ホーム画面に追加」するとアプリのように使えます。

---

## 地震速報 / Earthquake Alert

P2P地震情報の WebSocket API を使用しています。

- 福岡県で震度 2 以上の地震が発生した場合に即座に読み上げ
- 緊急地震速報（警報）にも対応
- 自動再接続機能あり（切断時に5秒後に再接続）

---

## 設定変更 / Configuration

すべての設定は `config.py` で一元管理しています：

```python
# 読み上げ速度を変更（1.0=普通、1.4=少し速め）
TEMPO = "1.4"

# 朝の天気アナウンス時刻を変更
MORNING_HOUR   = 7
MORNING_MINUTE = 30

# 地震速報の最小震度を変更
MIN_INTENSITY = 2
```

---

## システム構成 / Architecture

```
ユーザー
  ↓（声で呼びかけ）
AT-CSP1（マイク）
  ↓（USB音声入力）
Raspberry Pi 3
  ├── smart_speaker.py
  │     ├── 音声認識（speech_recognition）
  │     ├── Gemini API（質問・回答）
  │     ├── Weather API（天気・PM2.5）
  │     ├── Pollen API（花粉）
  │     └── gTTS（音声合成）→ AT-CSP1（スピーカー）
  ├── dashboard_server.py（Flask / port 5000）
  └── earthquake.py（P2P地震情報 WebSocket）
```

---

## 使用ライブラリ / Dependencies

```
google-genai        # Gemini AI API
speechrecognition   # 音声認識
gtts                # Google Text-to-Speech
flask               # ダッシュボード Web サーバー
flask-cors          # CORS 対応
psutil              # システム情報取得
websocket-client    # 地震速報 WebSocket
sox                 # 音声変換・速度調整
```

---

## セキュリティ / Security

- `config.py` は `.gitignore` で除外済み（APIキーは公開されません）
- ダッシュボードは同一 Wi-Fi ネットワーク内からのみアクセス可能
- GitHub リポジトリは Private 設定推奨

---

## 📝 ライセンス / License

MIT License

---

## 使用API・サービス / Credits

- [Google Gemini API](https://ai.google.dev)
- [Open-Meteo](https://open-meteo.com) — 天気予報
- [OpenWeatherMap](https://openweathermap.org) — PM2.5
- [Google Pollen API](https://developers.google.com/maps/documentation/pollen) — 花粉情報
- [P2P地震情報](https://www.p2pquake.net) — 地震速報

---

*子供たちのために 🌸*
