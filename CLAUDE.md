# Voice Dev — Claude Code 作業ルール

## 絶対原則: タスク実行フロー

すべてのタスクは以下の順序で実行すること。例外なし。

1. **MD更新（着手前）** — 該当する要件定義・設計ドキュメントに「実装方針」「変更スコープ」を記載する
2. **実装** — コードを変更する
3. **MD更新（進捗）** — 実装中に設計が変わった場合、MDに反映する
4. **MD更新（完了）** — 実装完了後、MDに「実装済み」状態を記録する
5. **git commit + GitHub push** — 変更をコミットしてプッシュする

```
MD更新(着手前) → 実装 → MD更新(完了) → git commit → git push
```

### ドキュメントがない場合

既存のドキュメントが対象タスクをカバーしていない場合は、`docs/` 配下に新規MDを作成してから実装する。

---

## プロジェクト概要

音声入力でAIと会話しながらアプリ開発できる環境。FastAPI + バニラJS。ビルドステップなし。

```
server/main.py           # FastAPI + WebSocket サーバー
server/claude_client.py  # Claude CLI ラッパー（セッション継続 + ワンショット生成）
server/tools.py          # ファイル操作・git・シェル実行
server/idea_store.py     # アイデアDB（ideas/ のMD管理）
server/proposal_store.py # 改善提案チェックリスト（proposals/ のMD管理）
server/secrets_store.py  # 環境変数・接続情報（~/.voice-dev/secrets/）
server/autodev.py        # 自動開発スケジューラ（30分おきに1タスク）
client/index.html        # フロントエンド（単一ファイル、4モード: 定義/実装/企画/提案）
ideas/                   # 要件定義書の蓄積先（1送信 = 1MD）
proposals/               # アプリ別の改善提案MD + 自動開発ログ
docs/                    # 設計・要件ドキュメント
```
