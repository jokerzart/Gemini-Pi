#!/bin/bash
echo "=== ジェミニパイ 起動中 ==="

# 音量を最大に設定
amixer -c 2 sset 'PCM' 100%

# ALSAの設定を保存
sudo alsactl store

# 古いプロセスを終了
pkill -f smart_speaker.py
pkill -f dashboard_server.py
pkill -f earthquake.py
sleep 1

# 全部バックグラウンドで起動
python3 ~/dashboard_server.py &
sleep 1
python3 ~/earthquake.py &
sleep 1
python3 ~/smart_speaker.py &

echo "=== 起動完了 ==="
echo "ダッシュボード: http://gemini-pi.local:5000"
echo "地震速報: 監視中"
