# 生成パイプライン パース修正

## 概要

定義モード（アイデア生成）と提案モードの AI→パース→MD保存→自動実装パイプラインに5件のバグがあり、生成結果が消失・不完全になるケースを修正する。

## 変更スコープ

- `server/proposal_store.py` — `parse_generated()` の正規表現とフォールバック処理
- `server/main.py` — `_run_idea()` / `_run_propose()` のテキスト収集ロジック

## バグと修正方針

### バグ1: parse_generated() — 部分マッチ時にフォールバック未実行
- **原因**: `if tasks: return tasks` で1件でもマッチすると即returnし、未マッチ行のフォールバック処理がスキップされる
- **修正**: プライマリ正規表現の後、未マッチ行もフォールバック正規表現で処理して `tasks` に追加する

### バグ2: parse_generated() — **太字**がタイトル・説明に残留
- **原因**: フォールバック正規表現が `**` を除去しない
- **修正**: タイトル・説明から `*` を strip する

### バグ3: parse_generated() — 全角コロン区切りで説明分離失敗
- **原因**: `_DASH_RE` の後に `\s+` を要求するが、`：`の直後にスペースがないケースがある
- **修正**: `\s+` を `\s*` に変更（区切り文字があればスペースなしでも分離する）

### バグ4: _run_idea() — result_text フォールバックなし
- **原因**: run_oneshot の result イベントのテキストを収集していない
- **修正**: _run_propose() と同様に result_text を result_buf で収集し、buf が空の場合のフォールバックとして使用する

### バグ5: _run_propose() — result_text がUIに非表示
- **原因**: result_text チャンクで `continue` しているためキューに入らない
- **修正**: continue を削除し、キューにも入れてUI表示する

## ステータス

- [x] 実装済み（2026-07-07）

## 変更ファイル

- `server/proposal_store.py`: `_DASH_RE` から `ー`（長音）と `-`（ハイフン）を除外、`_GEN_RE` に `\**` 追加で太字対応、`\s+` → `\s*` で全角コロン対応、`parse_generated()` のフォールバックを常に実行するよう変更、`_clean_md()` 追加で `**` 除去
- `server/main.py`: `_run_idea()` に `result_text` フォールバック追加、`_run_propose()` の `result_text` を UI に表示
- `client/index.html`: `result_text` メッセージタイプを `text` と同様にチャットに表示
