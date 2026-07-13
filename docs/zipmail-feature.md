# ZIP送付モード（📦 送付タブ）

## 目的

指定フォルダ下のすべてのファイル、または個別に指定したファイルをZIP化し、
メール（宛先デフォルト: koki.n.shukatsu@gmail.com）に添付して送付できるようにする。

## 実装方針

### UI（client/index.html）

- ヘッダーのモード切替に第5のタブ **「📦 送付」**（mode: `zipmail`）を追加する
- モード色: `--mode-zipmail: #3fd68a`（緑）
- 画面フロー: ワークスペース選択 → プロジェクト選択（既存picker流用）→ 送付画面
- 送付画面（`showZipmailScreen`）:
  - プロジェクト内のファイルをフォルダごとにグループ表示し、チェックボックスで選択
  - フォルダ行のチェックボックスで配下ファイルを一括選択/解除
  - 「全選択 / 全解除」ボタン
  - 選択件数と合計サイズをフッターに表示
  - 宛先入力欄（デフォルト: koki.n.shukatsu@gmail.com）
  - 「📦 ZIP化して送信」ボタン
  - Gmail認証情報が未設定の場合は画面上部に設定フォームを表示
- チャット入力・マイクは本モードでは無効化する

### サーバー（server/main.py）

- `GET /api/zipmail/files?project_path=` — 送付対象ファイル一覧
  - `/api/project/files` と同様の走査だが、150KBのサイズ上限を撤廃し、
    各ファイルの `size` を返す（除外: 隠しファイル・`_IGNORE_DIRS`・バイナリ拡張子は含める）
- `POST /api/zipmail/send` — `{project_path, paths[], to}` を受け取り:
  1. 各パスを検証（ホームディレクトリ配下・実在ファイルのみ）
  2. インメモリでZIP作成（arcnameはproject_pathからの相対パス）
  3. ZIPサイズが20MB超ならエラー（Gmail添付上限25MBへの安全マージン）
  4. 秘密ストア（アプリ名 `gmail`）の `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` で
     smtp.gmail.com:465（SSL）から送信。SMTP処理は `asyncio.to_thread` で実行
- `GET /api/zipmail/config` — Gmail認証情報の設定済みかどうかを返す

### 認証情報

- Gmailの**アプリパスワード**を使用（2段階認証必須）
- 保存先: `~/.voice-dev/secrets/gmail.env`（既存 secrets_store を流用）
  - `GMAIL_ADDRESS=送信元Gmailアドレス`
  - `GMAIL_APP_PASSWORD=アプリパスワード16桁`

### 変更スコープ

| ファイル | 変更内容 |
|---|---|
| `client/index.html` | 送付タブ追加、モード色CSS、送付画面UI + JS |
| `server/main.py` | `/api/zipmail/files`・`/api/zipmail/send`・`/api/zipmail/config` 追加 |
| `docs/zipmail-feature.md` | 本ドキュメント（新規） |

## 実装状態

- [x] サーバーAPI実装
- [x] クライアントUI実装
- [x] 動作確認（`/api/zipmail/config`・`/api/zipmail/files`・`/api/zipmail/send` の応答、
      ホーム外パスの403、未設定時のエラーメッセージを確認済み。
      実際のGmail送信はアプリパスワード登録後にUIから確認すること）

## 使い方

1. ヘッダーの「📦 送付」タブ → ワークスペース → プロジェクトを選択
2. 初回のみ: 画面上部のフォームに送信元Gmailアドレスとアプリパスワードを登録
   （アプリパスワードは https://myaccount.google.com/apppasswords で発行。2段階認証が必要）
3. ファイルまたはフォルダにチェック → 宛先確認（デフォルト: koki.n.shukatsu@gmail.com）→「📦 ZIP化して送信」
