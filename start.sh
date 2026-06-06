#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SESSION="voice-dev"

# .envを読み込む
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "エラー: ANTHROPIC_API_KEY が設定されていません"
  echo "  .env ファイルに ANTHROPIC_API_KEY=sk-ant-... を追記してください"
  exit 1
fi

PORT="${PORT:-8000}"

# Tailscale起動
echo "Tailscaleを起動中..."
sudo tailscale up 2>/dev/null || true
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")

LOCAL_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' || hostname -I | awk '{print $1}')

echo "==================================="
echo "  Voice Dev を起動中..."
echo "==================================="
echo ""
echo "  PC アクセス:     https://localhost:${PORT}"
echo "  スマホアクセス:  https://${TAILSCALE_IP:-$LOCAL_IP}:${PORT}"
echo ""
echo "==================================="

# tmuxセッションが既に存在するか確認
if tmux has-session -t "$SESSION" 2>/dev/null; then
  # サーバーが実際にポートをリッスンしているか確認
  if ss -tln 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${PORT}\$"; then
    echo "  tmux セッション '$SESSION' は既に起動中です (port ${PORT} 応答あり)"
    echo ""
    echo "  再接続: tmux attach -t $SESSION"
    echo "==================================="
    exit 0
  else
    echo "  tmux セッション '$SESSION' は存在しますが port ${PORT} で応答がありません"
    echo "  セッションを破棄して再起動します..."
    tmux kill-session -t "$SESSION" 2>/dev/null || true
  fi
fi

# tmuxセッション作成（window 0: サーバー、window 1: claude）
tmux new-session -d -s "$SESSION" -n "server" -x 220 -y 50

# window 0: サーバー起動
tmux send-keys -t "$SESSION:server" "cd '$SCRIPT_DIR/server' && .venv/bin/python main.py" Enter

# window 1: claude起動
tmux new-window -t "$SESSION" -n "claude" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION:claude" "claude" Enter

# claudeウィンドウをアクティブにする
tmux select-window -t "$SESSION:claude"

echo ""
echo "  tmux セッション '$SESSION' を作成しました"
echo ""
echo "  セッションに入る: tmux attach -t $SESSION"
echo "  切断後の再接続:   tmux attach -t $SESSION"
echo ""
echo "  ウィンドウ切り替え: Ctrl+b → 0 (サーバー) / 1 (claude)"
echo "  セッション終了:     tmux kill-session -t $SESSION"
echo "==================================="
