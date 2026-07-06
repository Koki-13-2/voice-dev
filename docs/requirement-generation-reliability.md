# AI生成パイプラインの信頼性強化 — 出力契約・確実な保管・自動実装への連携

> ステータス: **実装済み**
> 作成日: 2026-07-07 / 実装完了: 2026-07-07

## 背景（デバッグで確認した問題）

定義モード（アイデア→要件定義書）と提案モード（改善提案生成）は、AIの出力書式がプロンプト頼みで、
システム側の読み取り・保管・自動実装への連携に以下の穴がある。

| # | 問題 | 影響 |
|---|------|------|
| 1 | 出力書式の契約が弱い（前置き・コードフェンス・見出し混入に無防備） | 要件定義書に前置きが混入して保存される / 提案が0件パースになる |
| 2 | 書式違反時の検証・自動リトライがない | 生成失敗がそのままユーザーに返る（1回の失敗で終わり） |
| 3 | パース失敗時に生出力が破棄される（`raw_preview` 300文字のみ） | 生成コストが無駄になり、原因調査もできない |
| 4 | `ideas/` `proposals/` が自動 git commit されない | **実測: `proposals/voice-dev.md` が未コミットのまま**。マシン障害で蓄積が消える |
| 5 | 自動開発の多重実行ガードがない | **実測: 同一タスク #1 が 01:05 に2回実行された**（uvicorn reload 等でループが複数走ると重複実行） |
| 6 | 自動実装タスクがアプリの要件定義書（`requirements/`）を参照しない | アイデア由来の要件と提案実装が乖離する |

## 実装方針

### A. 出力契約（sentinel方式）

AIの返答から機械的に確実に抽出できるよう、プロンプトで明示的なマーカーを義務付ける。

- **定義モード**: 要件定義書全体を `<<<IDEA_START>>>` / `<<<IDEA_END>>>` で挟んで出力させる
- **提案モード**: 提案リストを `<<<PROPOSALS_START>>>` / `<<<PROPOSALS_END>>>` で挟んで出力させる

サーバー側抽出は3段フォールバック:

1. sentinel 区間を抽出（最優先・確実）
2. sentinel がない場合: コードフェンス除去 → 定義は最初の `# ` 見出し以降、提案は全文パース
3. `result_text`（stream-json の result イベント）でも 1→2 を再試行（既存フォールバック維持）

### B. 検証 + 自動リトライ（1回）

- 定義: 抽出後に「`# ` タイトルがある」「必須セクションが2つ以上ある」を検証
- 提案: パース結果が1件以上あるかを検証
- 失敗時は「書式違反である」ことを明示した矯正プロンプトで **1回だけ自動再生成**（ストリームはUIにも流す）

### C. 生出力の確実なキャッシュ

- `cache/idea/<timestamp>.txt`, `cache/propose/<app>-<timestamp>.txt` に**毎回**生出力を保存（成功/失敗問わず）
- `cache/` は `.gitignore` に追加（デバッグ・復旧用のローカルキャッシュ）
- パース失敗時のイベントにキャッシュパスを含め、UIから追跡可能にする

### D. git による確実な保管（自動コミット）

- 新規 `server/gitutil.py`: `commit_and_push(paths, message)` — best-effort（失敗しても本処理は止めない、タイムアウト付き、`asyncio.to_thread` でノンブロッキング）
- 対象タイミング:
  - アイデア保存時（`ideas/<id>.md`）
  - 提案追記時（`proposals/<app>.md`）
  - 自動開発タスク完了時（`proposals/<app>.md` + `autodev-log.md`）

### E. 自動開発の多重実行ガード

- `~/.voice-dev/autodev.json` に `claim: {app, id, at}` を記録し、実行**前**にクレームを書き込む
- 別プロセス/リロード後のループは「30分以内にクレーム済みのタスク」をスキップ
- 実行完了・失敗時にクレームをクリア

### F. 自動実装へのインプット連携

- autodev タスク実行プロンプトに、アプリの `requirements/` 配下の要件定義書（アイデア由来含む）を読んでから着手する指示を追加
- 提案タスクの実装が要件定義と整合するようにする

## 変更スコープ

| ファイル | 変更 |
|---------|------|
| `server/gitutil.py` | 新規 — best-effort git commit/push |
| `server/idea_store.py` | `extract_document()`（sentinel/フェンス/見出しフォールバック）、`validate_document()`、保存時 git commit |
| `server/proposal_store.py` | `extract_block()`（sentinel抽出）、追記/完了時 git commit |
| `server/autodev.py` | クレーム式多重実行ガード、requirements参照指示、完了時 git commit |
| `server/main.py` | プロンプトの sentinel 契約化、`_run_idea`/`_run_propose` の抽出→検証→リトライ→キャッシュ化、イベント拡張（`parsed`/`cache_file`） |
| `client/index.html` | `proposals_updated` の parsed/added 表示、リトライ中の案内表示 |
| `.gitignore` | `cache/` 追加 |
| `tests`（scratch） | 抽出/パースのユニットテスト + 実 claude CLI での E2E 検証 |

## 実装状況

- [x] A. sentinel 出力契約（`<<<IDEA_START/END>>>` / `<<<PROPOSALS_START/END>>>`、3段フォールバック抽出）
- [x] B. 検証 + 自動リトライ（定義: タイトル+セクション3つ以上 / 提案: 1件以上パース。違反時は矯正プロンプトで1回再生成、UIに `notice` トースト）
- [x] C. 生出力キャッシュ（`cache/idea/` `cache/propose/` に毎回保存、失敗イベントにパス添付、`.gitignore` 済み）
- [x] D. git 自動コミット（`gitutil.commit_and_push` best-effort — アイデア保存/実装開始/提案追記/自動開発完了時）
- [x] E. 多重実行ガード（`autodev.json` の `claim` + TTL 30分。実測されていた同一タスク2重実行を防止）
- [x] F. requirements 連携（autodev タスクプロンプトに要件定義書の参照指示を追加）
- [x] 検証（ユニット + 実CLI E2E）

### デバッグで発見・修正した追加バグ

| バグ | 症状 | 修正 |
|------|------|------|
| `proc.kill()` が正常終了後に `ProcessLookupError` を投げる | 生成成功でも**空メッセージのエラー**になり「生成失敗」と表示される | `run_oneshot` / `send_message` の finally で捕捉 |
| `_TASK_RE` がカタカナ長音「ー」・ハイフンをタイトル区切り扱い | 「エラーハンドリング」が「**エラ**」に切り詰められ、更新のたびに行が壊れる | 保存形式の区切りを「 ` — ` 」に限定した正規表現に修正 |

### 検証結果（実 claude CLI / haiku）

- 定義モード E2E: sentinel 抽出成功 → frontmatter付きMD保存 → 構造検証OK → git保管呼び出しOK
- 提案モード E2E: sentinel 抽出で **10件パース/10件追加** → チェック → `next_task()` が自動開発キューとして正しく返却
- タイトルラウンドトリップ: 長音・ハイフン入りタイトルが保存→読込→更新で不変
- クレームガード: 有効クレームでスキップ、TTL失効で解放、None で解除
- gitutil: 一時リポジトリで commit 成功・無変更時 no-change・push失敗時も本処理継続
