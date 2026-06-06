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

  PC アクセス:     http://localhost:8000
  スマホアクセス:  http://100.65.1.43:8000

  Ctrl+C で停止
===================================
```

スマホからは `http://100.65.1.43:8000`（TailscaleのIP）でアクセスする。

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

1. `tailscale ip -4` でIPを再確認する
2. スマホのTailscaleアプリが起動しているか確認する
3. サーバーが起動しているか確認する（`curl http://localhost:8000`）
