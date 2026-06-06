# WebSocket切断耐性アーキテクチャ 要件定義

## 背景・問題

現在の `server/main.py` では、WebSocketハンドラーがClaude処理を直接ストリーミングしている。

```
[クライアント] ←→ [WebSocketハンドラー] → claude_client.send_message() → チャンク送信
```

この構造では **WebSocket切断 = Claude処理中断** となる。

- `async for chunk in client.send_message(...)` はWebSocket送信と同一コルーチン内で実行
- クライアント切断時に例外が発生し、Claude処理が途中で止まる
- 再接続しても途中から再開できず、最初からやり直しになる

---

## 提案アーキテクチャ

```
[クライアント]  ←→  [WebSocket]  →  [Queue/session_id]  ←  [Background Task]
                        ↑                                         ↑
                    切断しても                                  継続実行
                    再接続で続き受信                           claude_client.send_message()
```

WebSocket層とClaude処理層を分離し、Queueを介して非同期に連携する。

---

## 変更スコープ

**対象ファイル: `server/main.py` のみ**

---

## 実装要件

### 1. `TaskManager` クラスの追加

セッションごとに以下を管理するクラスを追加する。

| 属性 | 型 | 説明 |
|------|----|------|
| `queues` | `dict[str, asyncio.Queue]` | session_id → チャンクキュー |
| `tasks` | `dict[str, asyncio.Task]` | session_id → バックグラウンドタスク |

**メソッド:**

- `create_task(session_id, coroutine)` — バックグラウンドタスクを生成・登録
- `get_or_create_queue(session_id)` — Queueを取得、なければ作成
- `is_running(session_id)` — タスクが実行中か確認
- `cleanup(session_id)` — タスク完了後にQueueとTaskを削除

### 2. WebSocketハンドラーの改修

#### チャット受信時

```
1. session_id を決定（既存セッションまたは新規生成）
2. TaskManager.get_or_create_queue(session_id) でQueueを取得
3. asyncio.create_task() でClaude処理をバックグラウンド起動
4. Queueからチャンクを読み出し、クライアントへ送信
```

**バックグラウンドタスク内の処理:**

```python
async for chunk in claude_client.send_message(...):
    await queue.put(chunk)
await queue.put(None)  # 終端マーカー
```

#### 切断時

- WebSocket切断例外をキャッチしてもバックグラウンドタスクはキャンセルしない
- Queueへのバッファリングを継続
- Queueサイズ上限（例: 1000チャンク）を設けてメモリ溢れを防止

#### 再接続時

1. クライアントが同じ `session_id` を送信
2. `TaskManager.is_running(session_id)` で既存タスクを確認
3. 既存Queueのバッファをドレインしてデリバリー再開
4. タスクが既に完了していた場合はQueueの残りチャンクを送信して終了

---

## セッション管理

| 項目 | 仕様 |
|------|------|
| session_id の生成 | `crypto.randomUUID()` (クライアント側) |
| session_id の保存 | `sessionStorage` + `localStorage` の両方に保存 |
| session_id の復元 | リロード時: sessionStorage → localStorage の順にフォールバック |
| セッション有効期限 | タスク完了後 + 一定時間（例: 5分）で自動削除 |
| 最大並行セッション数 | 制限なし（必要に応じて上限を設ける） |

### session_id 保存戦略

```
sessionStorage  ← 同一タブ内の通常遷移
localStorage    ← モバイルでタブがメモリ解放された場合のフォールバック
```

- `sessionStorage` はページリロード（F5）では維持されるが、iOS Safari 等でタブがバックグラウンドで解放されると消える
- `localStorage` をフォールバックにすることで、タブ再開後も同じ session_id で再接続でき、実行中タスクを継続受信できる
- 新しいタブでは `sessionStorage` が空のため `localStorage` の既存 ID を引き継ぐ（同一人物の個人利用ツールとして許容範囲）

---

## エラーハンドリング

| ケース | 対処 |
|--------|------|
| バックグラウンドタスク内の例外 | Queueにエラーオブジェクトを `put` し、送信側でハンドリング |
| 存在しない session_id での再接続 | エラーレスポンスを返し、新規セッション開始を促す |
| Queueが上限に達した場合 | タスクを一時停止（`asyncio.Queue` の `maxsize` で自動ブロック） |
| タスクのタイムアウト | 未実装（将来的に `asyncio.wait_for` で対応可能） |

---

## メッセージフォーマット（WebSocket）

既存フォーマットに `session_id` フィールドを追加する。

**クライアント → サーバー:**

```json
{
  "type": "chat",
  "message": "ユーザー入力",
  "session_id": "optional-既存セッションID"
}
```

**サーバー → クライアント（セッション通知）:**

```json
{
  "type": "session",
  "session_id": "生成されたセッションID"
}
```

**サーバー → クライアント（チャンク）:**

```json
{
  "type": "chunk",
  "content": "テキスト断片",
  "session_id": "セッションID"
}
```

---

## 非機能要件

- バックグラウンドタスクはサーバープロセス内で動作（外部ブローカー不要）
- `asyncio` のみ使用（追加ライブラリなし）
- 変更は `server/main.py` に閉じ、他ファイルへの影響なし

---

## ページリロード耐性（実装済み）

### 問題

モバイルブラウザ（iOS Safari 等）では、タブがバックグラウンドでメモリ解放されると `sessionStorage` が消える。
その結果、再接続時に新しい session_id が生成され、サーバー側で実行中のタスクと紐づかなくなる。

### 解決策

`client/index.html` の SESSION_ID 初期化を以下のように変更：

```javascript
// 変更前
const SESSION_ID = (() => {
  let id = sessionStorage.getItem('sessionId');
  if (!id) { id = generateId(); sessionStorage.setItem('sessionId', id); }
  return id;
})();

// 変更後
const SESSION_ID = (() => {
  let id = sessionStorage.getItem('sessionId');
  if (!id) {
    id = localStorage.getItem('sessionId') || generateId();
    sessionStorage.setItem('sessionId', id);
    localStorage.setItem('sessionId', id);
  }
  return id;
})();
```

### 再接続フロー（サーバー側は変更なし）

```
1. ユーザーがページをリロード / タブを再開
2. クライアント: localStorage から旧 session_id を復元
3. サーバー: task_manager.is_running(session_id) == True を検出
4. サーバー: {"type": "thinking"} を送信
5. サーバー: _drain_queue() で残チャンクを配信
6. クライアント: thinking インジケーターが表示され、レスポンスが続きから表示される
```
