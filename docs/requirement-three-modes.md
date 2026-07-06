# 3モード機能拡張 — 要件定義 / 要件実装 / 追加提案蓄積

> ステータス: **実装済み**
> 作成日: 2026-07-06 / 実装完了: 2026-07-06

## 背景・目的

Voice Dev を「思いついたアイデアを貯める → 実装する → 実装後も勝手に育つ」開発サイクル全体を回せる環境に拡張する。

## モード構成

既存の「⚡ 開発」「📝 企画」に加え、ヘッダーのモード切替を4つにする。

| モード | ボタン | 役割 |
|--------|--------|------|
| 要件定義 | 💡 定義 | 1送信 = 1要件定義書。AIが自動でMD化しアイデアDBに蓄積 |
| 要件実装 | ⚡ 実装 | 既存の開発モードを拡張。アイデアDBからの実装はフォルダ自動作成。本番接続テスト・秘密情報管理を追加 |
| 企画 | 📝 企画 | 既存のまま（プロジェクト単位の要件MD管理） |
| 追加提案蓄積 | 🔧 提案 | アプリを指定するとAIが多角的な改善提案を生成。チェックした項目を30分おきに1タスクずつ自動開発 |

---

## ① 要件定義モード（アイデアDB）

### 要件

- ユーザーの1送信（音声/テキスト）を、AIが構造化された要件定義書MDに書き起こして保存する
- すべてMDで管理（`ideas/` ディレクトリ、gitで履歴管理）
- アプリから過去のアイデア一覧を閲覧できる
- 未着手のアイデアに ★ を付けられる（優先マーク）

### 設計

- 保存先: `voice-dev/ideas/<YYYYMMDD-HHMMSS>.md`
- フロントマター:

```markdown
---
id: 20260706-153000
title: 家計簿アプリ
status: 未着手        # 未着手 | 実装中 | 実装済み
starred: false
created: 2026-07-06 15:30
app_dir:              # 実装開始時にセット
---
```

- 本文構成（AI生成）: `# アプリ名` / 概要 / ターゲットユーザー / 解決する課題 / 主要機能（表） / 画面構成 / データ / 技術スタック案 / MVPスコープ / 元のアイデア（原文）
- 生成はワンショットの Claude CLI 実行（セッション継続なし、ツール不使用、純粋なMD出力）

### API

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/ideas` | アイデア一覧（フロントマター解析済みJSON） |
| POST | `/api/ideas/star` | ★ トグル `{id, starred}` |
| DELETE | `/api/ideas/{id}` | アイデア削除 |
| POST | `/api/ideas/implement` | 実装開始 `{id, workspace}` → フォルダ自動作成 |

- WebSocket: `{type:"chat", mode:"idea", text}` → 生成ストリーム → `{type:"idea_saved", idea:{...}}`

---

## ② 要件実装モード（既存開発モードの拡張）

### 要件

- 現行 voice-dev の開発モードをベースとする（既存アプリディレクトリ・手動作成ディレクトリは今まで通り使える）
- アイデアDBから実装するものは自動的にフォルダを切って開発を進める
- 本番環境を意識した接続テスト: スマホ画面確認 / Google Cloud 接続 / LINE 送信テスト
- 環境変数・接続情報を保管する安全な場所を用意する

### 設計

**アイデアからの実装開始** (`POST /api/ideas/implement`):

1. タイトルから安全なディレクトリ名を生成（ASCII化できない場合 `app-<id>`）
2. `~/<workspace>/<dir>/` を作成し `git init`
3. 要件定義書本文を `<dir>/requirements/要件定義書.md` にコピー
4. アイデアのフロントマターを更新（`status: 実装中`, `app_dir` セット）
5. クライアントは実装モードでそのプロジェクトを選択し、要件定義書を plan_file として開発チャットを開始

**秘密情報ストア**:

- 保存先: `~/.voice-dev/secrets/<アプリ名>.env`（ディレクトリ 700 / ファイル 600、gitリポジトリ外）
- API: `GET /api/secrets?app_name=`（値はマスク表示） / `POST /api/secrets` / `DELETE /api/secrets`
- 開発チャット実行時、対象アプリの秘密情報を Claude CLI サブプロセスの環境変数として注入する（AIがテストコード等から参照可能）

**本番接続テスト**（実装モードのクイックアクション）:

| ボタン | 動作 |
|--------|------|
| 📱 スマホ確認 | AIにHTTPS起動+アクセスURL提示を依頼するプロンプト送信 |
| 📤 LINEテスト | `POST /api/test/line` — 秘密ストアの `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_USER_ID` でプッシュ送信 |
| ☁ GCloud確認 | `POST /api/test/gcloud` — `gcloud auth list` / プロジェクト設定を確認して返す |
| 🔐 環境変数 | 秘密情報モーダルを開く（キー一覧・追加・削除） |

---

## ③ 追加提案蓄積モード（自動開発）

### 要件

- アプリを指定するとAIがコードを解析し、様々なレベル/角度から改善案を提案する
- 提案はチェックボックス付きMDで蓄積される
- チェックした項目を、30分おきに1タスクずつAIが自動実装する（外出中・会社にいても開発が進む）

### 設計

**提案ファイル**: `voice-dev/proposals/<アプリ名>.md`

```markdown
---
app: stock-visualizer
app_path: /home/kokinagano/private-dev/stock-visualizer
---

# stock-visualizer 改善提案

- [ ] 【UI/UX/小】ダークモード対応 — 目に優しくする <!-- id:1 -->
- [x] 【機能/中】CSVエクスポート — 分析結果を保存 <!-- id:2 -->
- [x] 【性能/大】仮想スクロール — 大量データ対応 <!-- id:3 done:2026-07-06T16:00 -->
```

- `[x]` = 自動開発キューに投入、`done:` = 実装済み
- 提案の角度: 機能 / UI/UX / 性能 / セキュリティ / テスト / 運用、規模: 小 / 中 / 大
- 生成: ワンショット Claude CLI（対象アプリを `--add-dir`、既存提案を重複回避のため提示）
- WebSocket: `{type:"chat", mode:"propose", project_path, text(任意の観点指示)}` → `{type:"proposals_updated"}`

**自動開発スケジューラ** (`server/autodev.py`):

- 設定: `~/.voice-dev/autodev.json` — `{enabled, interval_min: 30, model, last_run}`
- FastAPI startup で asyncio バックグラウンドループ起動（60秒ごとに判定）
- `enabled` かつ前回実行から `interval_min` 経過で、全提案ファイルから「チェック済み・未完了」の先頭タスクを1件実行:
  - `claude -p "<タスク実装+テスト+git commit指示>" --dangerously-skip-permissions` を対象アプリディレクトリで実行（タイムアウト25分）
  - 完了後 `done:<timestamp>` を付与し、`proposals/autodev-log.md` に実行ログを追記
- API: `GET/POST /api/autodev`（ON/OFF・間隔・モデル変更）, `GET /api/autodev/log`

---

## 変更スコープ

| ファイル | 変更 |
|---------|------|
| `server/idea_store.py` | 新規 — アイデアMDのCRUD・フロントマター解析 |
| `server/proposal_store.py` | 新規 — 提案MDの解析・チェック更新・次タスク取得 |
| `server/secrets_store.py` | 新規 — `~/.voice-dev/secrets/` の管理 |
| `server/autodev.py` | 新規 — 30分間隔の自動開発ループ |
| `server/claude_client.py` | ワンショット生成 `run_oneshot()` 追加、`send_message` に環境変数注入対応 |
| `server/main.py` | 上記API追加、WSモード分岐（idea/propose）、startupでスケジューラ起動 |
| `client/index.html` | モードボタン4つ化、アイデアDB画面、提案画面、自動開発トグル、秘密情報モーダル、本番テストクイックアクション |
| `ideas/` `proposals/` | 新規ディレクトリ（`.gitkeep`） |

## 実装状況

- [x] サーバー: アイデアDB（idea_store.py + `/api/ideas*` + WS `mode:"idea"`）
- [x] サーバー: 秘密情報ストア・接続テスト（secrets_store.py + `/api/secrets` + `/api/test/line|gcloud`、開発チャットへの環境変数注入）
- [x] サーバー: 提案生成・チェックリスト（proposal_store.py + WS `mode:"propose"` + `/api/proposals*`）
- [x] サーバー: 自動開発スケジューラ（autodev.py、startup起動、60秒tick、1タスク最大25分、`proposals/autodev-log.md` にログ）
- [x] クライアント: 4モードUI（💡定義 / ⚡実装 / 📝企画 / 🔧提案、アイデアカード+★、提案チェックリスト+自動開発トグル、秘密情報モーダル、本番テストクイックアクション）

### 実装メモ

- 要件定義書生成・提案生成は `run_oneshot()`（セッション継続なしの claude CLI 実行）
- アイデアの実装開始は同一アイデアに対して冪等（既存 app_dir があればそれを返す）
- 提案の重複はタイトル一致でスキップ。提案IDはファイル内連番
- 自動開発ONにした直後は `last_run` をクリアし、60秒以内に最初のタスクが実行される
- ストアモジュールはラウンドトリップテスト済み（保存→解析→更新→削除）
