# PC側セットアップ・操作手順

## 前提条件

- WSL2 (Ubuntu) が使える状態
- Python 3.10 以上
- Anthropic APIキー取得済み

---

## 初回セットアップ

### 1. APIキーを設定する

```bash
cd ~/voice-dev
nano .env
```

以下を記入して保存（Ctrl+O → Enter → Ctrl+X）：

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
PORT=8000
```

### 2. セットアップスクリプトを実行する

```bash
cd ~/voice-dev
./setup.sh
```

### 3. Tailscaleをインストール・ログインする

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

表示されたURLをブラウザで開いてログインする。

TailscaleのIPを確認しておく：

```bash
tailscale ip -4
# 例: 100.65.1.43
```

---

## 毎回の起動手順

```bash
cd ~/voice-dev
./start.sh
```

起動すると以下が表示される：

```
===================================
  Voice Dev を起動中...
===================================

  PC アクセス:     https://localhost:8000
  スマホアクセス:  https://<マシン名>.<tailnet名>.ts.net:8000

  Ctrl+C で停止
===================================
```

スマホからは表示された `https://xxxxx.ts.net:8000`（TailscaleのMagicDNS名）でアクセスする。

サーバーは音声入力（マイクAPI）に必要な HTTPS で起動する。`start.sh` が起動のたびに
TailscaleのMagicDNS名に対する信頼済みTLS証明書（Let's Encrypt発行）を
`tailscale cert` で自動発行・更新し `server/cert.pem` / `server/key.pem` に保存する。

**重要:** 必ずIPアドレス（`https://100.65.1.43:8000`など）ではなく、表示された `.ts.net` の
ホスト名でアクセスすること。IPアドレスでアクセスすると証明書のCNと一致せず、特にiPhone Safariで
「ページは開けるがWebSocketだけ繋がらない（接続マークが赤のまま）」という症状が起きる
（自己署名証明書の警告を突破してもWebSocketはその信頼を引き継がないため）。

---

## 停止する

サーバーを起動したターミナルで `Ctrl+C`。

---

## Tailscaleが切れた場合

```bash
sudo tailscale up
```

---

## APIキーを更新する

```bash
nano ~/voice-dev/.env
```

`ANTHROPIC_API_KEY=` の行を新しいキーに書き換えてサーバーを再起動する。

---

## トラブルシューティング

### サーバーが起動しない

```bash
# 仮想環境を再作成
cd ~/voice-dev
rm -rf server/.venv
./setup.sh
```

### ポート8000が使用中

```bash
# 使用中のプロセスを確認・終了
lsof -i :8000
kill -9 <PID>
```

または `.env` の `PORT=8000` を別の番号（例: `8080`）に変更する。

### スマホから繋がらない

1. スマホのTailscaleアプリが起動・ログイン済みか確認する
2. サーバーが起動しているか確認する（`curl -k https://localhost:8000`）
3. スマホでは必ず `.ts.net` のホスト名でアクセスする（IPアドレスではなく）。
   PC側で `tailscale status` を実行し `Self` の `DNSName` を確認する

### アプリ画面は開けるが「サーバーに接続中です」から進まない（接続マークが赤のまま）

WebSocket (wss://) が確立できていない状態。多くの場合、IPアドレスで自己署名証明書に
アクセスしていることが原因（特にiPhone Safari）。

1. スマホのURLがIPアドレスではなく `.ts.net` ホスト名になっているか確認する
2. `.ts.net` ホスト名でもダメな場合、PC側で証明書を発行し直す：
   ```bash
   sudo tailscale set --operator=$USER   # 初回のみ
   cd ~/voice-dev
   TS_DNS_NAME=$(tailscale status --json | python3 -c "import json,sys; print(json.load(sys.stdin)['Self']['DNSName'].rstrip('.'))")
   tailscale cert --cert-file=server/cert.pem --key-file=server/key.pem "$TS_DNS_NAME"
   ```
   その後 `./start.sh` でサーバーを再起動する
