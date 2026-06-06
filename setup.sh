#!/bin/bash
set -e

echo "=== Voice Dev セットアップ ==="

# Python仮想環境
cd "$(dirname "$0")/server"

if [ ! -d ".venv" ]; then
  echo "[1/3] 仮想環境を作成..."
  python3 -m venv .venv
fi

echo "[2/3] 依存パッケージをインストール..."
.venv/bin/pip install -q -r requirements.txt

# .envファイル確認
cd ..
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "⚠️  .env ファイルを作成しました。"
  echo "   ANTHROPIC_API_KEY を設定してください:"
  echo "   nano voice-dev/.env"
  echo ""
  exit 1
fi

echo "[3/3] セットアップ完了!"
echo ""
echo "起動コマンド:"
echo "  cd voice-dev && ./start.sh"
