# アウトプットPDFのプレビュー

## 目的

プロジェクトが生成したアウトプット（PDFファイル）を、voice-dev の画面から
ブラウザの新タブでプレビューできるようにする。

## 実装方針

### サーバー（server/main.py）

- `GET /pdf-view?path=` を追加（`/md-view` と同じ配置・同じ検証方針）
  - 拡張子が `.pdf` であること
  - 実在すること
  - ホームディレクトリ配下であること（外なら403）
  - `Content-Disposition: inline` で返し、ブラウザ内蔵ビューアでプレビュー表示させる

### クライアント（client/index.html）

- 「📦 送付」画面のファイル一覧で、`.pdf` のファイル名をリンク化し、
  クリックで `/pdf-view` を新タブで開く（👁 アイコン付き）
- ファイル一覧APIはZIP送付用の `/api/zipmail/files`（サイズ上限なし）を既に使っており、
  PDFも一覧に含まれるため、新規APIは不要

## 変更スコープ

| ファイル | 変更内容 |
|---|---|
| `server/main.py` | `GET /pdf-view` 追加 |
| `client/index.html` | 送付画面のPDF行をプレビューリンク化 + リンク用CSS |
| `docs/pdf-preview.md` | 本ドキュメント（新規） |

## 実装状態

- [x] サーバー実装
- [x] クライアント実装
- [x] 動作確認（200 + `content-type: application/pdf` + `content-disposition: inline`、
      非PDF・ホーム外パスの拒否を確認済み）

## 使い方

「📦 送付」タブでプロジェクトを開くと、ファイル一覧の `.pdf` が緑のリンク（👁付き）になる。
クリックすると新タブでブラウザのPDFビューアが開く。
