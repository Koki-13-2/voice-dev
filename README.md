# Voice Dev

スマホの音声入力でAIと会話しながらアプリ開発できる環境。

## 必要なもの

- Python 3.10+
- Anthropic APIキー
- スマホ（同一LAN または Tailscale経由）

## セットアップ

### 1. APIキーを設定する

```bash
cd ~/voice-dev
cp .env.example .env
nano .env
```

`.env` を編集：

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
PORT=8000
```

### 2. セットアップスクリプトを実行する

```bash
./setup.sh
```

Python仮想環境の作成とパッケージインストールが行われる。

### 3. サーバーを起動する

```bash
./start.sh
```

起動するとアクセス先のURLが表示される：

```
  PC アクセス:     http://localhost:8000
  スマホアクセス:  http://192.168.x.x:8000
```

## スマホからアクセスする

### 同一Wi-Fi環境の場合

`start.sh` に表示された `http://192.168.x.x:8000` をスマホのブラウザで開く。

### 外出先でも使いたい場合（Tailscale）

WSL2側：

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4   # このIPをスマホからアクセスに使う
```

スマホ側：

1. App Store / Google Play で **Tailscale** をインストール
2. 同じアカウントでログイン
3. `http://<tailscale-ip>:8000` をブラウザで開く

## 使い方

### 音声入力

1. 画面下の **「タップして話す」** ボタンを押す
2. 日本語で話す（例：「ログイン画面を作って」）
3. 認識が終わると自動でAIに送信される

### テキスト入力

テキストエリアに直接入力して **↑ボタン** または **Enterキー** で送信。

### プロジェクトの切り替え

画面右上のパス表示をタップするとプロジェクトパスを変更できる。  
デフォルトは `/home/kokinagano`。

### 会話のリセット

右上の **「リセット」** ボタンで会話履歴をクリアする。

## AIへの指示の例

```
「srcディレクトリの構成を見せて」
「Expressでシンプルなサーバーを作って」
「ログイン機能を追加して」
「テストを実行して結果を教えて」
「変更をgit commitして」
「mainにマージして」
```

## システム構成

```
スマホ (ブラウザ)
  ↓ Web Speech API（音声→テキスト）
  ↓ WebSocket
FastAPI サーバー (WSL2 :8000)
  ↓ Claude API (claude-sonnet-4-6)
  ↓ ツール実行
    - read_file    ファイル読み取り
    - write_file   ファイル書き込み
    - list_directory  ディレクトリ一覧
    - run_shell    シェルコマンド実行（git, npm, python等）
    - create_directory  ディレクトリ作成
  ↑ 結果をスマホに返却
```

## ファイル構成

```
voice-dev/
├── server/
│   ├── main.py          # FastAPI + WebSocket サーバー
│   ├── claude_client.py # Claude API + ツール実行ループ
│   ├── tools.py         # ファイル操作・git・シェル実行
│   └── requirements.txt
├── client/
│   └── index.html       # スマホ用UI
├── .env                 # APIキー設定（gitで管理しない）
├── .env.example         # テンプレート
├── setup.sh             # 初回セットアップ
└── start.sh             # 起動スクリプト
```

## トラブルシューティング

### スマホから繋がらない

- PCとスマホが同じWi-Fiに繋がっているか確認する
- Windowsファイアウォールでポート8000を許可する
  - 「Windowsセキュリティ」→「ファイアウォール」→「受信の規則」→ポート8000を追加
- Tailscaleを使う場合、両端末でTailscaleが起動しているか確認する

### 音声認識が動かない

- iOSはSafari、AndroidはChromeを使う（他のブラウザはWeb Speech API非対応の場合あり）
- HTTPSでないと音声入力がブロックされる場合がある（ローカルネットワーク内のHTTPは通常OK）

### APIエラーが出る

- `.env` の `ANTHROPIC_API_KEY` が正しく設定されているか確認する
- `./start.sh` を再起動する
