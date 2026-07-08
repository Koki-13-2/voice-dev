# 自動開発 実行ログ

## 2026-07-07 01:05 — voice-dev #1 `parse_generated`の正規表現を緩和して番号付きリストに対応

- 結果: ✅ 成功

```
完了しました。

**実施内容:**
- `server/proposal_store.py` の `_GEN_RE` を `^[-*]` のみから `^\d+[.)]\s*|[-*•·▸►]\s*|\s*` に拡張し、`1. 【...】` 形式の番号付きリストをパース可能に
- ダッシュ文字も `[—–\-ー:：]` で統一マッチ（em/en/ハイフン/長音/コロン）
- `_FALLBACK_RE` による2段階パースも追加済み（正規表現失敗時のフォールバック）
- 動作確認: 番号付き・箇条書き・混在すべて正しくパース（3件/2件/3件）
- コミット・プッシュ完了: `56d5835`

```

## 2026-07-07 01:05 — voice-dev #1 `parse_generated`の正規表現を緩和して番号付きリストに対応

- 結果: ✅ 成功

```
このタスクはすでに完了・コミット済みです（`56d5835 fix: parse_generatedの正規表現を緩和して番号付きリストに対応`）。

実装内容の確認：
- `_GEN_RE` を `^[-*]\s*` のみから `^(?:\d+[.)]\s*|[-*•·▸►]\s*|\s*)` に拡張し、番号付きリスト (`1. 【...】`) に対応
- ダッシュ文字のバリエーション（`—–-ー:：`）を統一サポート
- `_FALLBACK_RE` によるフォールバックパーサーを追加（正規表現が0件でも `【】` 含む行を緩くマッチ）

`git push` は不要（`origin/main` と同期済み）。タスクは実装・コミット・プッシュまで完了しています。

```

## 2026-07-07 08:38 — gh_portal #4 未使用テーブルjob_tasks/job_task_comments/job_task_readsの画面実装

- 結果: ✅ 成功

```
Warning: no stdin data received in 3s, proceeding without it. If piping from a slow command, redirect stdin explicitly: < /dev/null to skip, or wait longer.
プッシュ完了。実装内容を確認します。

実装が完了しました。変更内容のまとめ：

**AdminJob.tsx（管理者側）に追加:**
- `AdminJobTaskSection` — 案件詳細の下部に表示されるタスク一覧セクション。タスクカード（未読バッジ・ステータスバッジ）、並び替え（↑↓）、「タスクを追加」ボタンを含む
- `JobTaskThread` — タスクカードタップで開く全画面チャットスレッド。Supabaseリアルタイム購読付き、開いた時点で既読更新（`job_task_reads` upsert）、管理者はステータスをドロップダウンで変更可能
- `JobTaskFormSheet` — タスク作成・編集・削除フォーム（ボトムシート形式）。削除は確認ダイアログ付き

**Job.tsx（講師側）に追加:**
- `TeacherJobTaskSection` — 受注確定済み（`isApproved`）の案件のみ表示。閲覧・投稿のみ（作成・削除・並び替えボタンなし）
- `TeacherJobTaskThread` — 講師用チャットスレッド（既読管理・リアルタイム更新）

要件定義書（`requirements/admin/screens/subscreens/job-tasks.md`）に従い、管理者フローと講師フローを実装しました。TypeScriptビルドも通過し、コミット・プッシュ済みです。

```

## 2026-07-07 09:02 — gh_portal #1 database.types.tsの再生成

- 結果: ✅ 成功

```
完了しました。

**実施内容まとめ:**

1. **`database.types.ts` 再生成** — `supabase gen types` で12テーブルを追加:
   - `student_subjects`, `departments`, `meeting_feedbacks`, `payroll_rules`, `payroll_records`, `job_submission_comments`, `job_field_comments`, `job_field_submissions`, `job_application_comments`, `job_field_task_comments`, `meeting_records`, `universities/university_subjects`

2. **`(supabase as any)` キャスト全廃** — 9ファイル43箇所を修正

3. **ビルドエラー修正** (型が厳密になったことで露見した3件):
   - `LifePatternContext.tsx`: `life_patterns`の`week_start`（DB必須カラム）に現在日付を補完
   - `AdminJob.tsx`: `is_pinned`（DB未存在カラム）を削除、`created_by`の型解決
   - `AdminPayroll.tsx`: `payroll_records.status`を`PayStatus`にキャスト

4. `npm run build` で型チェック・ビルドが **✓ 全件通過**を確認してからコミット・プッシュ

```

## 2026-07-07 09:28 — gh_portal #2 MeetingRecordContextのlocalStorage→DB移行

- 結果: ✅ 成功

```
完了しました。

**変更内容まとめ：**

- **`src/lib/MeetingRecordContext.tsx`** — localStorage を完全削除。`useEffect` で Supabase の `meeting_records` テーブルから取得するよう変更。
  - 講師ロール：`teacher_id` で絞り込み、生徒名を `profiles!meeting_records_student_id_fkey` でJOIN
  - 生徒ロール：`student_id` で絞り込み、講師名を `profiles!meeting_records_teacher_id_fkey` でJOIN
  - `addRecord()` はDBへの挿入は行わず、既にSupabaseに挿入済みのレコードをオプティミスティックに先頭追加するのみ（実挿入は `MtgWorkflowScreen.handleSave` 側）

- **`src/pages/Dashboard.tsx`** — StudentDashboard から localStorage フォールバック（`localPending`）を削除。`pendingRecord` は直接 `dbPendingRecord` を参照するように簡略化。

```

## 2026-07-07 09:58 — gh_portal #3 MeetingFeedbackContextのlocalStorage→DB移行

- 結果: ✅ 成功

```
完了しました。

**実施内容:**

1. **`MeetingFeedbackContext.tsx`**: localStorage を完全に削除し、`MeetingRecordContext` と同パターンで `useEffect` + Supabase の `meeting_feedbacks` テーブルからDBフェッチに変更。`addFeedback` は DB insert 済みの楽観的ステート更新のみ。

2. **`Dashboard.tsx`** (関連バグ修正):
   - フィードバック送信後に `meeting_records.feedback_pending = false` を更新 → 次回ロード時に通知が再表示されるバグを修正
   - 完了画面クローズ時に `dbPendingRecord` をクリア → 同セッション内の再表示も防止

```

## 2026-07-07 10:30 — gh_portal #5 Contents画面の書き込み機能追加

- 結果: ✅ 成功

```
完了しました。

**実装内容：**

- **`contents` クエリに `url` を追加**し、`content_progress` からも `last_position_sec` / `total_watch_sec` / `started_at` / `is_completed` を取得するように拡張
- **`VideoDetail` コンポーネント**を新規追加：
  - lecture カードタップで `.modal-overlay` オーバーレイを表示
  - `last_position_sec` から自動で再生再開（`onLoadedMetadata` で seek）
  - **1秒ごとの tick** で実際の再生時間（`total_watch_sec`）を正確に積算
  - **30秒ごとの定期保存** + 動画終了時 + オーバーレイ閉じ時に `content_progress` へ UPSERT（`onConflict: 'user_id,content_id'`）
  - `watch_pct >= 90` で `is_completed = true` を自動セット
  - シーク後退してもパーセントが下がらないよう `maxPctRef` で管理
- **`handleProgressSaved`** で保存後にカードの進捗バッジをリアルタイム更新

```

## 2026-07-07 10:58 — gh_portal #6 Dashboard.tsxのクエリ分割とキャッシュ

- 結果: ✅ 成功

```
完了しました。実施内容のまとめ：

**実装内容**

`src/pages/Dashboard.tsx` の `TeacherDashboard` 直前に、60秒TTLのモジュールレベルキャッシュを追加しました。

| 変更箇所 | 内容 |
|---|---|
| キャッシュ変数定義 | `StudentsCache` 型 + `studentsCache` + `STUDENTS_CACHE_TTL = 60_000` |
| `fetchStudents` 冒頭 | 同一 `teacherId` のキャッシュが有効なら5テーブルのフェッチを全スキップ |
| `fetchStudents` 末尾 | フェッチ結果をキャッシュに書き込み |
| `handleStudentChange` | 講師が生徒データ編集した際にキャッシュも更新（staleデータ防止） |
| meetings リアルタイム購読 | 生徒の承諾/拒否がWebSocketで届いた際にキャッシュも更新 |

**効果**  
一覧↔詳細画面を行き来するたびに `homework_tickets` 等5テーブルを再フェッチしていた重複クエリが、60秒以内であればゼロになります。60秒経過後は自動的に再フェッチして鮮度を保ちます。

```

## 2026-07-07 11:28 — gh_portal #7 life_pattern_slotsテーブルの使途確認と整理

- 結果: ✅ 成功

```
完了しました。

**実施内容:**

| 変更 | 詳細 |
|------|------|
| `src/lib/database.types.ts` | `life_pattern_slots` テーブル定義（Row/Insert/Update/Relationships）を削除 |
| `src/lib/supabase.ts` | `LifePatternSlot` 型エクスポートを削除 |
| `supabase/migrations/20260707000001_drop_life_pattern_slots.sql` | `DROP TABLE IF EXISTS public.life_pattern_slots` マイグレーション追加 |

**根拠:** コード全体を検索した結果、`life_pattern_slots` テーブルはどのコンポーネントからも参照されていませんでした。`LifePatternContext.tsx` は `life_patterns.blocks` JSON列のみを使ってスロットデータを管理しており、別テーブルは完全に未使用の二重管理状態でした。`tsc --noEmit` でも型エラーなし。

```

## 2026-07-07 12:00 — gh_portal #8 AdminMessages画面のメッセージ送信DB保存

- 結果: ✅ 成功

```
実装完了。変更内容まとめ：

**作成・変更ファイル:**
- `supabase/migrations/20260707000002_message_logs.sql` — `message_logs` テーブル新規作成（`sent_by`, `target_type`, `target_ids[]`, `message`, `sent_at`）と RLS（`is_admin`/`is_owner` のみ読み書き可）
- `src/pages/admin/AdminMessages.tsx` — 送信ボタンに `handleSendStudents` / `handleSendJobRemind` を追加し `message_logs` に INSERT。履歴タブで直近50件を取得・表示。jobリマインドの textarea を controlled に変更
- `src/lib/database.types.ts` — `message_logs` の型定義を追加（TypeScript 型エラー解消）

**動作:**「LINE送信」ボタンを押すと `message_logs` にログが保存され、「送信履歴」タブで確認できます。LINE連携が未確定のためノート付きで表示し、実際の外部送信は連携確定後の拡張に委ねています。

```

## 2026-07-07 12:28 — gh_portal #10 get_university_rankingのRPCエラーハンドリング追加

- 結果: ✅ 成功

```
実装完了です。変更内容：

- **`fetchError` ステート追加** — RPC が `error` を返したときに `true` にセット
- **`retryCount` ステート追加** — `useEffect` の依存配列に含め、インクリメントで再フェッチをトリガー
- **エラー表示UI** — 「ランキングの取得に失敗しました」メッセージと「再試行」ボタンを既存のローディング/空状態と同じスタイルで表示
- エラー後に再試行ボタンを押すと `retryCount` が増加し、`useEffect` が再実行されてRPCを再呼び出しする

```

## 2026-07-07 13:01 — gh_portal #12 tutorialDone状態のDB永続化

- 結果: ✅ 成功

```
実装完了です。変更内容：

**問題**: `completeTutorial()` が localStorage のみに書き込んでいたため、ブラウザデータ消去でチュートリアル完了状態がリセットされる。

**修正内容**:
1. **マイグレーション** (`20260707000003_...sql`): `profiles` テーブルに `tutorial_done boolean NOT NULL DEFAULT false` を追加
2. **`AuthContext.tsx`**:
   - `fetchProfile()` で `tutorial_done` をDBから取得
   - `completeTutorial()` で Supabase への書き込みを追加（楽観的更新）
   - ログイン時にDB値を正として同期。DB未書き込み（失敗キャッシュ）を検知したら自動リトライ
3. **`database.types.ts`**: `profiles` の Row/Insert/Update に `tutorial_done` の型定義を追加

要件書の「完了フラグの送信失敗時はローカルにキャッシュし、次回起動時にリトライする」も対応済みです。なお、Supabase 側でのマイグレーション適用（`supabase db push` 等）は別途必要です。

```

## 2026-07-07 13:32 — gh_portal #13 Chat.tsx講師ビューの生徒リストDB化

- 結果: ✅ 成功

```
完了しました。変更内容のサマリー：

**変更箇所：** `src/pages/Chat.tsx`

- `students: Student[]` / `studentsLoading: boolean` の state を追加
- `useEffect` を新設し、講師ログイン時に `teacher_student_assignments` テーブルから `teacher_id = 現在ユーザー` のレコードを取得 → `profiles` テーブルで名前を結合して生徒リストを構築
- `STUDENTS.find(...)` × 2 を `students.find(...)` に置換
- 講師チャットタブ・AIチャットタブの生徒一覧を `students.map/filter` に置換
- ローディング中・担当生徒なし・検索ヒットなしの各空状態メッセージを追加

```

## 2026-07-07 14:02 — gh_portal #14 Chat.txチャンネル一覧のDB化

- 結果: ✅ 成功

```
実装完了。変更内容のまとめ:

- **削除**: `CHANNELS` ハードコード定数（3件のモックデータ）
- **追加**: `channels` / `channelsLoading` state
- **追加**: `chat_rooms` テーブルから `type='group'` のルームを取得する `useEffect`（Supabase RLS により自分がメンバーのルームのみ返る）
- **簡略化**: `initChannelRoom` 内の「名前でDBを検索」ロジックを削除。`activeChannel` がそのまま `chat_rooms.id`（UUID）になったため不要
- **追加**: チャンネル一覧にローディング中・空状態のUI

```

## 2026-07-07 14:32 — gh_portal #15 GoalPanelの受験日表示をDBから取得

- 結果: ✅ 成功

```
実装完了しました。

**変更内容：**
- `GoalPanel` に `examDateLabel` state を追加
- `student_profiles` の select に `exam_type` を追加取得
- `exam_date` が取得できたとき、`YYYY-MM-DD（曜日）{exam_type}` 形式でラベルを構成しstateに保存（`exam_type` がなければ日付＋曜日のみ）
- `exam_date` が未設定の場合は「受験日未設定」を表示
- `daysLeft` の計算には引き続き同じ `exam_date` を使用

```

## 2026-07-07 15:03 — gh_portal #17 Dashboard生徒画面のスケジュール読み込み中表示追加

- 結果: ✅ 成功

```
完了しました。

**変更内容:**

- `Dashboard.tsx`: `pillsLoading` state を追加し、`fetchDashboard()` 実行開始時に `true`、完了時（または失敗時）に `false` をセット
- `DailyPanel` に `pillsLoading` プロップを追加し、`pills.length === 0` かつローディング中は回転スピナー + 「読み込み中...」を表示、ローディング完了後にスケジュールがない場合のみ「この日の予定はまだ設定されていません」メッセージを表示
- `globals.css`: `@keyframes spin` アニメーションを追加

```

## 2026-07-07 15:33 — gh_portal #18 saveLifeSlotsToDbのdelete→insert原子性確保

- 結果: ✅ 成功

```
完了です。

**変更内容:**
- `saveLifeSlotsToDb` の delete / insert 両操作の戻り値を分割代入で受け取り、エラーがあれば即 `throw`
- delete 失敗時はデータ消失のリスクなくアーリーリターン
- **insert が delete 後に失敗した場合**（データ消失シナリオ）にエラーをスロー → 呼び出し元でキャッチ
- `saveSlotError` state を追加し、エラー時に画面上部へ「スケジュールの保存に失敗しました」バナーを 4 秒間表示
- push 済み（`main` @ `8e28d72`）

```

## 2026-07-07 16:03 — gh_portal #19 Timeline.tsxいいねトグルの失敗時ロールバック追加

- 結果: ✅ 成功

```
完了しました。

**変更内容:** `Timeline.tsx:478` の `toggleLike` 関数で、DB同期（Supabaseの `insert`/`delete`）の戻り値 `error` を取得し、エラー時に楽観的更新前の `liked`/`likes` 状態へ復元するロールバック処理を追加しました。

```

## 2026-07-07 16:39 — gh_portal #20 Practice.tsxレーダーチャート・成績推移のDB化

- 結果: ✅ 成功

```
完了です。実装内容をまとめます。

## 実施内容

**削除したもの:**
- `RADAR_SUBJECT_LIST`（固定科目リスト）
- `RadarSubject` 型
- `RADAR_SCORES`（ハードコードのスコア）
- `SCORE_HISTORY`（ハードコードの推移データ）

**追加・変更したもの:**

`FeedbackDashboard` コンポーネント内に DB 取得ロジックを追加:

1. **マイスコア集計**: `test_submissions → auto_score_results → tests` を結合し、`type='mock'` または `'past_exam'` の完了済み受験結果を科目別に集計
2. **生徒平均集計**: 同じテスト ID を受験した全ユーザーの `auto_score_results` から平均を算出
3. **科目リスト動的生成**: DB から取得した受験データに存在する科目のみを表示
4. **得点推移**: `submitted_at` でソートして時系列順に並べ、模試は `title`、過去問は `university·year` をラベルとして使用
5. **空状態対応**: データなし・ローディング中それぞれに適切なメッセージを表示

TypeScript 型チェック・ビルドともにエラーなし、`git push` 済みです。

```

## 2026-07-07 18:39 — gh_portal #16 LifePatternContextの楽観的更新ロールバック実装

- 結果: ✅ 成功

```
修正完了。

**変更内容** (`src/lib/LifePatternContext.tsx:107-114`):
- `.then(({ data }) => ...)` を `.then(({ data, error }) => ...)` に変更
- `error || !data` の場合、`setPatterns` でtempIdのエントリを `filter` で除去してロールバック
- 成功時は従来通り仮IDをDB UUIDに置き換え

これにより、ネットワーク障害・権限エラー・DB制約違反などで insert が失敗した際も、UIに幽霊パターンが残らなくなります。

```

## 2026-07-07 18:46 — gh_portal #11 Realtime購読の一元管理

- 結果: ✅ 成功

```
タスク完了しました。実装内容をまとめます。

---

## 実施内容

### 新規作成: `src/lib/useRealtime.ts`

`postgres_changes` 購読のライフサイクルを統一するカスタムフック：

- `channelName / table / event / filter / schema / enabled` オプションを受け取る
- `callbackRef` パターンを使用し、コールバックが変わっても不要な再購読が起きない
- `enabled: false` のとき購読を作成せず、`true` に変わったとき自動的に購読を開始・終了

### 修正: 4ファイル・11箇所

| ファイル | 対象コンポーネント | 購読数 |
|---|---|---|
| `Job.tsx` | SubmissionThread / TeacherFieldCommentThread / TeacherJobTaskThread | 3 |
| `AdminJob.tsx` | SubmissionChat / FieldCommentThread / FieldTaskChat / ApplicationChat / JobTaskThread | 5 |
| `Dashboard.tsx` | Dashboard（meetings UPDATE） | 1 |
| `Chat.tsx` | 講師DM / チャンネルタブ | 2 |

Chat.tsxは `realtimeSubRef` / `channelRealtimeRef` と手動 `cleanup()` 関数を削除し、`teacherRoomId` / `channelRoomId` state + `enabled: tab === 'teacher' && !!teacherRoomId` 条件でライフサイクルを制御するよう変更しました。

```

## 2026-07-07 18:46 — gh_portal #21 AssignNotification承諾・相談フローのエラーハンドリング追加

- 結果: ✅ 成功

```
実装完了です。変更内容をまとめます。

**実装した変更（`src/components/AssignNotification.tsx`）**

- `AssignNotificationManager` に `error` state を追加
- `handleAccept`：各DB操作（update→insert chat_room→insert room_members）の戻り値のエラーをチェックし、失敗時はエラーメッセージをセットしてearly returnする。UIは進まない
- `handleConsult`：各DB操作（update→profiles select→insert chat_room→insert room_members→insert message→update consult_room_id）を同様にチェック
- `AssignNotificationPopup` にエラーバナー（`an-error`）を追加。×ボタンで閉じられる

**`src/styles/globals.css`** にエラーバナーのスタイルを追加（赤系ボーダー・背景）

コミット `cbdc441` に全変更が含まれており、リモートにも反映済みです。

```

## 2026-07-07 18:50 — gh_portal #22 AdminStudents講師割り当て変更のエラーハンドリング追加

- 結果: ✅ 成功

```
完了しました。

**変更内容（`AdminStudents.tsx:940-968`）:**

- `upsert`（講師追加）と `delete`（講師削除）の両方で `{ error }` を受け取るよう変更
- エラーが発生した場合、`setStudents` で楽観的更新をロールバック（`assignedTeachers` を変更前の `current` に戻す）
- `alert()` でエラーメッセージをユーザーに通知してから `return`（既存の `alert` スタイルに合わせた）

これにより、DB反映に失敗してもUIが成功状態のままになる問題が解消されます。

```

## 2026-07-07 18:58 — gh_portal #23 Dashboard学習統計（studyStreak・weeklyStudyHours等）のDB集計

- 結果: ✅ 成功

```
実装完了。変更内容をまとめます。

---

**変更内容**: `Dashboard.tsx` の `fetchDashboard` 内、stats計算ブロックを拡張

1. **`homework_tickets` selectを拡張**: `actual_minutes, completed_at` を追加取得

2. **`weeklyStudyHours`（今週の学習時間）**: 当週月曜0:00以降に`completed_at`があるdoneチケットの`actual_minutes`（未記録なら`estimated_minutes`）を合計し、分→時間へ変換（小数1桁）

3. **`studyStreak`（連続学習日数）**: `completed_at`の日付セットを作り、今日から過去に向かって連続した日数をカウント（今日未完了の場合は昨日から起算）

4. **`overallProgress`（全体進捗）**: 全`homework_tickets`のうち`done`の割合をパーセント表示

```

## 2026-07-07 19:02 — gh_portal #24 Chat生徒ビューの担当講師一覧をteacher_student_assignmentsから取得

- 結果: ✅ 成功

```
完了しました。

**変更内容:**

- `ASSIGNED_TEACHERS` ハードコード定数（`山田 太郎`・`佐藤 涼子`）を削除
- `assignedTeachers` state を追加し、生徒ログイン時に `teacher_student_assignments` → `profiles` の順でDBからフェッチする `useEffect` を実装
- 3箇所のUI参照を置き換え：
  - 講師チャットのヘッダータイトル（担当なし時は「担当講師」と表示）
  - AIタブの「担当講師が全ルームに参加中」バナー（担当なし時は非表示）
  - AIルーム内のヘッダーピル（担当なし時は非表示）

```

## 2026-07-07 19:12 — gh_portal #25 Chat AIルームのメッセージDB永続化

- 結果: ✅ 成功

```
実装完了。変更内容のまとめ：

**実装内容**（`src/pages/Chat.tsx`）

- **`dbToAiChat()` 関数を追加**：`is_ai` フラグを見てAI送信者・ユーザー・講師を識別してChatMessage型に変換

- **状態追加**：
  - `aiRoomDbIdsRef`（useRef）：科目キー→DB UUIDのキャッシュ（再レンダリング不要）
  - `aiRoomsLoading`（useState）：ルーム入室時の読み込み表示用

- **AI初期化 useEffect 追加**：生徒がAIルームに入室したとき
  1. `room_members`を確認し、`type='ai'` `name='math'`等のルームを検索
  2. 存在しなければ`chat_rooms`に新規作成＋`room_members`に自分を追加
  3. `messages`テーブルからメッセージをロード（空なら初期デモデータ表示）

- **`handleAiSend()` をasync化**：
  - ユーザー送信メッセージ：`sender_id=user.id, is_ai=false` でDB挿入
  - AI応答メッセージ：`sender_id=user.id, is_ai=true` でDB挿入（既存RLSポリシーに適合、migration不要）
  - 楽観的UI更新後にDB挿入し、IDをDB由来のUUIDに置き換え

```

## 2026-07-07 19:15 — gh_portal #26 Chat面談招待モーダルの生徒スケジュールをdaily_schedule_slotsから取得

- 結果: ✅ 成功

```
実装完了。

変更内容：
- **削除**: `STUDENT_PILLS` ハードコード定数（6件の固定スロット）
- **`MeetingInviteModal` 改修**: `studentPills` プロップを `studentId: string` に置き換え
- **動的フェッチ**: モーダル内で `date` が変わるたびに `daily_schedule_slots` を Supabase からフェッチ。`homework_tickets → material_tickets` もJOINしてチケットラベルを取得
- **変換ロジック**: `ticket_id` があれば `type: 'task'`、なければ `type: 'life'`。ラベルはスロットの `label` → チケットの `material_tickets.label` → フォールバック `'学習予定'` の優先順で設定

```

## 2026-07-07 19:23 — gh_portal #27 room_members.last_read_atを用いたチャット未読バッジの実装

- 結果: ✅ 成功

```
実装完了。変更内容の概要：

**追加したヘルパー関数（モジュールレベル）：**
- `getRoomUnreadCounts(roomIds, lastReadAtMap, currentUserId)` — 各ルームで `last_read_at` 以降の他者メッセージ数を一括集計
- `markRoomAsRead(roomId, userId)` — `room_members.last_read_at` を現在時刻に更新

**fetchStudents の変更（講師向け生徒一覧）：**
プロフィール取得後、講師の DM ルームメンバーシップを取得 → 各生徒との DM ルームを特定 → `last_read_at` を参照して未読カウントを計算し `Student.unread` に反映。

**fetchChannels の変更：**
チャンネル取得後、自分の `room_members` レコード（`last_read_at` 含む）を取得 → チャンネルごとの未読カウントを計算し `Channel.unread` に反映。

**ルーム入室時の処理：**
- DM ルーム（講師→生徒）: `markRoomAsRead` で DB 更新 + 生徒リストの `unread` をクリア
- チャンネル: `markRoomAsRead` で DB 更新 + チャンネルリストの `unread` をクリア

```

## 2026-07-07 19:25 — gh_portal #28 Practice連続学習日数をtest_submissions提出日から動的算出

- 結果: ✅ 成功

```
実装完了。変更内容：

- `test_submissions` クエリに `submitted_at` を追加
- フェッチ完了後に提出日をSet化し、今日（または昨日）から遡って連続日数を算出する `streakCount` ロジックを追加
- `streak` stateを `PracticeHome` に prop 経由で渡し、バナーの固定値 `5` を `{streak}` に置換
- 未提出の場合は `0` 日が表示される

```

## 2026-07-07 19:32 — gh_portal #29 Practice添削フィードバック未読数をcorrections.is_read_by_studentから集計

- 結果: ✅ 成功

```
実装完了。変更内容のまとめ：

**`src/pages/Practice.tsx` への変更（3箇所）**

1. **未読数 state の追加**（`StudentPractice`）  
   `const [unreadCount, setUnreadCount] = useState(0)` を追加

2. **未読数フェッチの `useEffect` 追加**（`StudentPractice`）  
   `corrections` テーブルで `status = 'returned'` かつ `is_read_by_student = false` の件数を Supabase の `count` クエリで取得し、ホーム画面のバッジに反映

3. **既読更新の `useEffect` 追加**（`FeedbackDetail`）  
   `item.read === false` の場合のみ、`corrections.is_read_by_student = true` へ DB 更新し、`onRead` コールバック経由でカウントをデクリメント（要件「既読状態を自動で更新」に対応）

```

## 2026-07-07 19:37 — gh_portal #30 Timelineコメントいいねのテーブル新設とDB永続化

- 結果: ✅ 成功

```
実装完了。変更内容の概要：

**追加したもの**
- `supabase/migrations/20260707000005_comment_likes.sql` — `comment_likes` テーブル（`comment_id` + `user_id` の複合PK）とRLSポリシー3つ。リモートDBに適用済み。
- `database.types.ts` — `comment_likes` の型定義を追加

**修正したもの（`Timeline.tsx`）**
- `POST_SELECT` に `comment_likes ( user_id )` を追加し、コメント取得時にいいね情報を同時取得
- `rowToFeedPost` の `replyList` マッピングで `liked` / `likes` を `comment_likes` から算出（従来は `false` / `0` のハードコード）
- `toggleReplyLike` を `async` 関数に変更し、`post_likes` の `toggleLike` と同様にオプティミスティックUI + DBシンク + 失敗時ロールバックを実装

```

## 2026-07-07 19:44 — gh_portal #31 Timeline投稿の画像添付UI実装

- 結果: ✅ 成功

```
実装完了です。

## 変更内容

**`src/pages/Timeline.tsx`**
- `ImageAttachment` インターフェース（`file` + `previewUrl`）を追加
- `FeedPost` に `imageUrls?: string[]` を追加
- `POST_SELECT` に `image_urls` を追加し、DB取得時にフィードへ反映
- `postImages` / `questionImages` state を追加
- `closeComposer` でオブジェクトURLを revoke してリセット
- `handleAttachChange` で選択ファイルをプレビューURLとセットで保持
- `removeImage` で個別削除
- `uploadImages` で Supabase Storage (`post-images` バケット) にアップロードし公開URLを返す
- `submitPost` / `submitQuestion` で画像URLを `image_urls` カラムに保存
- コンポーザーUIに画像プレビューグリッド（サムネイル + ×ボタン）を表示
- フィードの投稿カードに添付画像を表示（1枚: 16:9横幅いっぱい、複数: 2カラム4:3グリッド）

**`src/styles/globals.css`**
- `.composer-images` / `.composer-image-item` / `.composer-image-thumb` / `.composer-image-remove` を追加
- `.post-images` / `.post-images--single` / `.post-images__img` を追加

> **注意**: Supabase ダッシュボードで `post-images` という名前のパブリックバケットを作成する必要があります。バケットが存在しない場合、テキスト投稿は正常に動作しますが、画像はアップロードされません（サイレントスキップ）。

```

## 2026-07-07 19:47 — gh_portal #32 announcements.body詳細表示の追加

- 結果: ✅ 成功

```
実装完了です。

**変更内容:**
- `BannerSlide` 型に `body` フィールドを追加
- Supabase クエリで `body` カラムを取得するよう更新（`select('id, title, body, banner_color')`）
- 非管理者ユーザーがバナースライドをタップすると `setAnnouncementDetail` で詳細ステートを更新
- `announcements.body` 本文を表示するボトムシートモーダルを既存パターンに合わせて追加（`announcement-detail__body` CSS）
- 管理者のバナー画像アップロード動作は変更なし

```

## 2026-07-07 19:53 — gh_portal #33 ProfileSheet編集画面のフィールド拡充

- 結果: ✅ 成功

```
実装完了です。

**変更内容（`ProfileSheet.tsx` の `ProfileEditView`）:**

- **フィールド追加**: 苗字・名前（漢字）/ 苗字・名前（カナ）を2列グリッドで表示、性別（チップ選択）、生年月日（date input）、郵便番号、住所
- **Supabase クエリ拡張**: `select` と `update` の両方に 9 フィールドを追加。全て `profiles` テーブルのカラム（オンボーディング用マイグレーションで追加済みのもの）
- **スクロール対応**: ヘッダー固定 + コンテンツエリアを `overflow-y: auto` のフレックスコンテナに変更し、フィールドが多くても 92vh のボトムシート内でスクロール可能
- **性別チップ**: 男性・女性・その他のボタングループ。同じものを再タップすると解除（トグル動作）

```

## 2026-07-07 20:01 — gh_portal #35 Practice演習問題QUESTIONSのDB化

- 結果: ✅ 成功

```
完了です。実施した内容をまとめます：

**変更内容：**

1. **`supabase/migrations/20260707000006_exercise_questions.sql`（新規）**
   - `exercise_questions` テーブルを新設（id, sort_order, subject, category, body, option_a〜d, answer, explanation, is_published, created_at）
   - RLS を有効化し、認証済みユーザーの `SELECT` と講師/admin の全操作を許可
   - 旧ハードコード2問（仮定法英文法）を初期データとして INSERT

2. **`src/pages/Practice.tsx`**
   - ハードコードの `QUESTIONS` 定数（29行）を削除
   - `activeQuestions` の初期値を `QUESTIONS` → `[]` に変更
   - `startQuiz` で `testId` がない場合に `exercise_questions` テーブルから `sort_order` 昇順で取得するよう変更

3. **`src/lib/database.types.ts`**
   - `exercise_questions` テーブルの型定義（Row/Insert/Update）を追加し TypeScript エラーを解消

> **注意：** マイグレーションは Supabase ダッシュボードまたは `supabase db push` で適用が必要です。適用後はサンプル2問が DB に入り、startQuiz(testId 未指定) 時に DB から取得されます。

```

## 2026-07-07 20:02 — gh_portal #36 Practice・TeacherPracticeのハードコード日付をnew Date()に修正

- 結果: ✅ 成功

```
完了しました。

- `Practice.tsx` L1011: `new Date('2026-04-16')` → `new Date()`
- `TeacherPractice.tsx` L147: `new Date('2026-04-14')` → `new Date()`

ビルド成功・push 済みです。これにより期限までの残日数（Practice の締切バッジ）と提出からの経過日数（TeacherPractice の「〇日前」表示）が常に実行時の現在日付を基準に計算されます。

```

## 2026-07-07 20:14 — gh_portal #37 Practice PdfViewerとTeacherPractice PdfPaneを実PDF表示に置換

- 結果: ✅ 成功

```
実装完了しました。変更内容をまとめます。

---

**変更内容**

**TeacherPractice.tsx — `PdfPane`**
- `totalPages` prop を廃止し、`url?: string` prop を追加
- URL がある場合: `<iframe>` でSupabase Storage の署名付きURLからPDFを直接表示 ＋「別タブで開く」リンク
- URL がない場合: 従来のグレープレースホルダー

- `PendingItem` / `ReturnedItem` に `studentPdfPath` / `modelPdfPath` フィールドを追加
- データロード時に `corrections` テーブルからパスを取得してセット
- `ReviewScreen` / `ReturnedDetailScreen` で `useEffect` により署名付きURL（有効期限1時間）を生成して `PdfPane` に渡す

**Practice.tsx — `PdfViewer`**
- `pages` prop を廃止し、`url?: string` prop を追加
- URL がある場合: `<iframe>` ＋「別タブで開く」リンク
- URL がない場合: グレープレースホルダー

- `FeedbackDetail` に `useEffect` を追加し、`corrections.student_pdf_path`（= `item.filename`）から署名付きURLを生成して `PdfViewer` に渡す
- 過去問問題用紙は `tests` テーブルにPDFカラムが未存在のため、プレースホルダーを維持

```

## 2026-07-07 20:18 — gh_portal #38 Dashboard GoalPanelのガントチャート日付範囲を動的算出

- 結果: ✅ 成功

```
完了しました。

**実装内容：**

- モジュールレベルの固定定数 `CHART_START`・`CHART_END`・`CHART_MONTHS`（2026年4〜7月ハードコード）を削除
- `buildChartRange(items, examDate?)` ヘルパーを追加：
  - 全教材の `startDate`/`endDate` と `exam_date` の最小・最大から月境界を算出
  - 最低 2 ヶ月分を保証するフォールバック付き
  - 月ラベル配列（`["4月", "5月", ...]`）を動的生成
- `dateToPct()` のシグネチャを `(dateStr, chartStart, chartEnd)` に変更してモジュール定数依存を排除
- **生徒用 GoalPanel**：Supabase からデータ取得後に `buildChartRange(built, sp.exam_date)` で算出し state に保持
- **講師用 TeacherGoalPanel**：レンダリング時に `buildChartRange(student.ganttItems, student.examDate)` で算出（IIFE 形式）

```

## 2026-07-07 23:47 — gh_portal #39 Dashboard講師ビューの生徒カードrecentRate・weeklyStudyHours・studyStreakをDB集計

- 結果: ✅ 成功

```
実装完了。変更内容：

**`fetchStudents` に2クエリ追加：**
- `test_submissions`（直近7日、`created_at >= 7日前`）→ `recentRate` 算出
- `daily_schedule_slots`（直近30日、`date >= 30日前`）→ `weeklyStudyHours` と `studyStreak` 算出

**各フィールドの算出ロジック：**
- `recentRate`: 直近7日に作成されたテスト提出のうち `status='completed'` の割合（%）
- `weeklyStudyHours`: 今週（月曜日以降）の `ticket_id IS NOT NULL`（宿題スロット）の `duration_minutes` 合計 ÷ 60
- `studyStreak`: 今日から遡って `daily_schedule_slots` に記録がある連続日数（最大30日）

```

## 2026-07-07 23:52 — gh_portal #40 Dashboard講師ビューのlastLoginをauth.usersのlast_sign_in_atから取得

- 結果: ✅ 成功

```
完了しました。実装内容をまとめます：

**変更内容：**

1. **マイグレーション追加** (`supabase/migrations/20260707000008_get_students_last_login.sql`)  
   `auth.users` にアクセスできる `SECURITY DEFINER` 関数 `get_students_last_login(uuid[])` を新設。複数の生徒IDの `last_sign_in_at` を一括返却。

2. **Dashboard.tsx** (`src/pages/Dashboard.tsx`)  
   - `Promise.all` に `supabase.rpc('get_students_last_login', ...)` を追加
   - 結果を `lastLoginMap` に変換（`M/D HH:MM` 形式にフォーマット）
   - `lastLogin: ''` → `lastLoginMap[sid] ?? '未ログイン'` に置換

3. **型定義更新** (`src/lib/database.types.ts`)  
   新RPC関数の引数・戻り値型を追加してビルドエラーを解消。

```

## 2026-07-07 23:56 — gh_portal #41 AdminMessages個別生徒選択のSupabase接続実装

- 結果: ✅ 成功

```
実装完了しプッシュしました。

変更内容：
- `StudentOption` 型を追加し、`students`・`selectedStudentIds`・`studentSearch`・`studentsLoading` の state を追加
- `studentTarget === 'select'` に切り替えた際、`profiles` テーブルから生徒一覧をレイジーロードするeffectを追加
- スタブの `<p>` を名前検索フィールド＋全選択チェックボックス＋スクロール可能なリストのピッカーUIに置き換え
- `handleSendStudents` で `select` モードのとき `target_ids` に選択済み生徒IDを渡すよう更新
- 送信ボタンは `select` モードで未選択の場合は無効化

```

## 2026-07-07 23:59 — gh_portal #42 Dashboard死コードTODAY_PILLSの削除

- 結果: ✅ 成功

```
完了。`Dashboard.tsx` の L29–37 にあった未使用定数 `TODAY_PILLS`（9行）を削除し、型チェックを通過後にコミット・push しました。

```

## 2026-07-08 00:07 — gh_portal #43 Job.tsx MOCK_JOBSフォールバックの削除とログイン必須化

- 結果: ✅ 成功

```
完了しました。

**変更内容：**
- `MOCK_JOBS` 定数（7件のモックデータ、141行）を削除
- `Job()` メインコンポーネントの `if (!useRealData) { setJobs(MOCK_JOBS); ... }` フォールバック分岐を削除
- `react-router-dom` の `Navigate` を import し、`session` が null の場合に `/login` へリダイレクト
- `useRealData` は常に `true` の定数に変更（サブコンポーネントへの prop は維持）

`ProtectedRoute` がルートレベルで既にログインガードをしていますが、`Job` コンポーネント内にも明示的な `<Navigate to="/login" replace />` を追加し、二重に保護しています。

```

## 2026-07-08 00:46 — gh_portal #44 AdminStudents lastLoginDaysAgoのDB接続

- 結果: ✅ 成功

```
実装完了です。

**変更内容** (`src/pages/admin/AdminStudents.tsx`)

`load()` 内で `subjectsMap` 取得後に `get_students_last_login` RPC を呼び出し、`last_sign_in_at` から現在日時までの日数差分を算出して `lastLoginDaysMap` に格納。生徒リスト構築時に `lastLoginDaysAgo: lastLoginDaysMap[p.id] ?? 0` で実値を反映しました。

- `last_sign_in_at` が null（未ログイン記録なし）の場合は 0 にフォールバック（誤警告を防ぐため）
- Dashboard.tsx の同 RPC 呼び出しパターンに準拠
- 警告バッジ「7日以上未ログイン」と詳細フィルターの `loginDaysMin/Max` が正常動作するようになります

```

## 2026-07-08 00:53 — gh_portal #45 AdminStudents メッセージテンプレートのDB永続化

- 結果: ✅ 成功

```
実装完了しました。変更内容をまとめます。

---

### 実装内容

**マイグレーション** (`supabase/migrations/20260708000001_message_templates.sql`)
- `message_templates` テーブルを新設（`id`, `name`, `sort_order`, `created_at`）
- RLS: `is_admin` または `is_owner` のユーザーのみ操作可能
- 従来の `DEFAULT_TEMPLATES` 5件を初期 seed として挿入

**型定義** (`src/lib/database.types.ts`, `src/lib/supabase.ts`)
- `message_templates` テーブルの Row/Insert/Update 型を追加
- `MessageTemplate` エクスポートを追加

**UI** (`src/pages/admin/AdminStudents.tsx`)
- `MessageComposer` を全面改修
  - マウント時に `message_templates` からロード（sort_order 順）
  - 追加: `INSERT` → レスポンスのレコードをローカル state に追加
  - 削除: 即時 UI 反映（楽観的更新） → `DELETE` をバックグラウンド実行

> **注意**: マイグレーション SQL はファイルとして追加済みですが、Supabase ダッシュボードの SQL エディタから `supabase/migrations/20260708000001_message_templates.sql` を手動実行する必要があります。

```

## 2026-07-08 00:57 — gh_portal #46 Dashboard weakPoints保存ボタンのSupabase永続化

- 結果: ✅ 成功

```
完了しました。

`Dashboard.tsx:4140-4149` の保存ボタン `onClick` を `async` 関数に変更し、`onChange` 呼び出しの前に `supabase.from('student_profiles').upsert({ id: student.id, memo: weakPoints }, { onConflict: 'id' })` を追加しました。これにより、講師が弱点メモを保存するたびに `student_profiles.memo` カラムに書き込まれ、再読み込み後も内容が保持されます。

```

## 2026-07-08 01:03 — gh_portal #47 Dashboard simulateStudentResponseデモコードの除去

- 結果: ✅ 成功

```
完了しました。

**変更内容：**
- `simulateStudentResponse` 関数（5行）を削除
- デモ用UIブロック（`{/* デモ：生徒応答シミュレーター（invited時のみ） */}` の `div` 全体、19行）を削除

ビルド成功・push 済みです。面談インビテーションの講師側送信・バッジ表示などの本番機能はそのまま維持されています。

```

## 2026-07-08 01:09 — gh_portal #48 Dashboard dailyComment死フィールドの除去

- 結果: ✅ 成功

```
完了。`TeacherStudentData` 型から `dailyComment: string` の定義（1999行目）と、オブジェクト生成時の `dailyComment: ''` 代入（3136行目）を削除しました。型チェック通過・push済みです。

```

## 2026-07-08 01:17 — gh_portal #49 Chat QUIZ_BANKのDB化

- 結果: ✅ 成功

```
完了しました。

**実装内容まとめ:**

- `QUIZ_BANK` 定数（52行）を削除し、代わりに `ROOM_SUBJECT_MAP`（roomId → 日本語科目名）と `fetchQuizForRoom` 非同期関数を追加
- `fetchQuizForRoom` は `exercise_questions` テーブルから対象科目の公開問題を最大20件取得し、ランダムに1問選んで `ChatMessage` 形式に変換（`answer` フィールドの 'A'〜'D' を 0-based インデックスに変換）
- `handleThreadSend` を `async` 化し、DBフェッチと700ms待機を `Promise.all` で並行実行することで応答速度を維持
- DBに問題がない場合は従来どおりテキスト応答にフォールバック
- ビルド成功・push 済み

```

## 2026-07-08 01:23 — gh_portal #50 Chat threadMessagesデモデータの除去と空状態UI追加

- 結果: ✅ 成功

```
完了しました。

**実施した変更：**

1. **`threadMessages` のデモデータ削除**（770-790行目）  
   `'a6'` キーに入っていたハードコードの鎖則クイズスレッドを除去し、初期値を `{}` に変更。

2. **`INIT_AI_MESSAGES` 定数の完全削除**  
   AIルームのデモメッセージ定数（数学・英語・物理・小論文のハードコード会話）を削除。

3. **DB取得ロジックの修正**  
   AIルーム入室時のメッセージ取得で、DB結果が0件の場合にデモデータへフォールバックしていたのを除去。DB保存済みのみ表示するように変更。

4. **空状態UI追加**  
   AIルーム内チャットエリアに、ロード完了後でメッセージが0件の場合の空状態UI（「まだ会話がありません。@AIを使ってAIに質問してみましょう。」）を追加。ThreadPanelの空状態は既存のものをそのまま活用。

```

## 2026-07-08 01:28 — gh_portal #51 Chat モックメッセージフォールバックを空状態UIに置換

- 結果: ✅ 成功

```
完了しました。

**変更内容：**
- `teacherChatMessages` / `channelMessages` の初期値を `TEACHER_MESSAGES` / `CHANNEL_MESSAGES` から `[]` に変更
- `initRoom` / `initChannelRoom` のリセット処理もそれぞれ `[]` に変更
- Supabase 0件時のフォールバック（`msgs.length > 0 ? ... : MOCK_DATA`）を除去し、素直に `msgs.map(...)` へ
- 講師チャット（生徒視点）、講師チャット（講師→個別生徒視点）、チャンネルの3箇所に「まだメッセージはありません」の空状態UIを追加

```

## 2026-07-08 01:35 — gh_portal #52 Onboarding志望校入力をuniversitiesテーブルのサジェスト選択に変更

- 結果: ✅ 成功

```
実装完了です。変更内容：

**変更ファイル**
- `src/pages/Onboarding.tsx` — `UniversityCombobox`コンポーネントを追加し、STEP 3の第一・第二・第三志望大学のinputを置き換え。`universities`テーブルから一括取得した候補を入力文字で絞り込み表示。第一志望選択時は`target_university_id`（FK）もDBに保存。
- `src/styles/globals.css` — `.onboarding-combobox` / `__list` / `__item` のスタイルを追加（絶対位置ドロップダウン、最大10件・200px、ホバーでオレンジ系ハイライト）。

**動作概要**
1. コンポーネントマウント時に`universities`テーブルを`sort_order`順で全件取得
2. ユーザーが文字を入力すると大学名を部分一致で絞り込み（最大10件表示）
3. 候補をクリックすると名前をセット（第一志望はIDもセット）
4. コンポーネント外クリックでドロップダウンを閉じる
5. リストにない大学名は自由テキストでも入力可能（後方互換性を維持）

```

## 2026-07-08 01:39 — gh_portal #53 AdminJob CATEGORY_OPTIONSの動的取得

- 結果: ✅ 成功

```
完了しました。

**変更内容まとめ：**

- `CATEGORY_OPTIONS` ハードコード定数を `FALLBACK_CATEGORY_OPTIONS` にリネーム（DB未取得時の安全網として保持）
- `AdminJob` に `categoryOptions` stateを追加（初期値はフォールバック）
- ジョブ一覧取得後、全行の `category_tags[]` を `flatMap` → `Set` で重複排除 → ソートして `setCategoryOptions` に設定。取得値が空の場合はフォールバックを使用
- `AdminJobForm` の props に `categoryOptions: string[]` を追加し、フォーム内のタグ選択ボタン描画に使用

```

## 2026-07-08 08:28 — gh_portal #54 AdminRoute・OwnerRouteのlocalStorage信頼脆弱性修正

- 結果: ✅ 成功

```
完了しました。

**修正内容**: `App.tsx` の `AdminRoute`・`OwnerRoute` を修正し、`loading || !profileReady` の間は常にローディング画面を表示するようにしました。

**修正前の問題点**:
- `loading=false` かつ `profileReady=false`（DBフェッチ中）の状態で `user.isAdmin=true`（localStorageキャッシュ）なら即座に管理画面へ入れていた
- DevToolsで `gh_portal_is_admin_<uid>` を `"true"` に書き換えると誰でも管理画面にアクセスできた

**修正後の動作**:
- `profileReady=true`（`fetchProfile`のDB確認完了）まで必ずローディング表示
- DB確定値のみで `isAdmin`/`isOwner` を判断するため、localStorageを改竄しても無効

```

## 2026-07-08 08:34 — gh_portal #55 Register.tsx pending_roleのsessionStorage注入防止

- 結果: ✅ 成功

```
完了しました。

**修正内容**: `AuthContext.tsx:109-122` の `SIGNED_IN` ハンドラで、`sessionStorage` から読み取った `pending_role` を `supabase.from('profiles').update(...)` に渡す前に `['student', 'teacher']` のホワイトリスト検証を追加しました。

- **修正前**: 任意の文字列（`'admin'` 等）をそのままDBに書き込んでいた
- **修正後**: `'student'` または `'teacher'` のみ許可。それ以外の値は `sessionStorage` から削除した上でスルーし、通常の認証フローへ続く（`updateUser` を呼ばないため SIGNED_IN の再発火もなく、リターンせず正常に state が更新される）

```

## 2026-07-08 08:43 — gh_portal #62 Admin5画面の共通データ取得フック（useAsyncLoad）抽出

- 結果: ✅ 成功

```
完了しました。

**実装内容：**

1. **`src/lib/useAsyncLoad.ts`** — 新規作成
   - `useEffect + cancelled + setLoading` パターンを汎用フックに抽出
   - `fn(isCancelled: () => boolean) => Promise<void>` を受け取り、`loading: boolean` を返す
   - deps 変更時に自動で `loading=true` にリセット
   - `try/finally` でエラー時もローディングが解除されるよう安全に実装

2. **`src/pages/admin/adminUtils.ts`** — 新規作成
   - `toInitial` を3ファイルから1か所に集約

3. **AdminUsers / AdminStudents / AdminPayroll / AdminDeliverables** — `useAsyncLoad` 置き換え＋`toInitial` import 変更

4. **AdminMessages** — 最初の `useEffect`（jobs + count 取得）を `useAsyncLoad` に置き換え（students の条件付き遅延ロードや logs 取得は構造が異なるため変更対象外）

```

## 2026-07-08 08:45 — gh_portal #56 storage.tsファイルアップロードのサイズ・ファイル名バリデーション追加

- 結果: ✅ 成功

```
完了しました。

**変更内容（`src/lib/storage.ts`）:**

- `MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024`（Supabase Storage の 50 MB 上限）を定数で定義
- `file.name.trim()` が空の場合は早期 `null` リターン
- `file.size > MAX_FILE_SIZE_BYTES` の場合は MB 値を含むエラーログとともに早期 `null` リターン

呼び出し元（`Job.tsx`, `Practice.tsx`）はすでに `null` チェックで対応済みのため、既存の挙動を壊さずにバリデーションが機能します。

```

## 2026-07-08 08:50 — gh_portal #57 Practice.tsx useEffect依存配列の[user]→[user?.id]修正

- 結果: ✅ 成功

```
`Practice.tsx:558` の `[user]` を `[user?.id]` に変更しました。これにより、ユーザーIDが変わらない限り（例: プロフィール更新など無関係なプロパティ変更）fetchTests が再実行されなくなります。コミットとpushも完了しています。

```

## 2026-07-08 08:57 — gh_portal #59 Chatタブ切替時の下書きテキスト分離管理

- 結果: ✅ 成功

```
実装完了です。

**変更内容：**

`Chat.tsx:749` の `const [draft, setDraft] = useState('')` を以下に置き換えました：

- `drafts: Record<string, string>` — タブ+ルームキーで引く辞書
- `draftKey` — `tab`・`selectedStudentId`・`activeChannel`・`selectedAiStudentId`・`activeAiRoomId` の組み合わせで自動計算
- `draft` と `setDraft` — 既存のすべての呼び出し箇所はそのまま動作する互換ラッパー

これにより、講師タブ→チャンネルタブ→AIタブと切り替えても、それぞれの入力中テキストが保持されます。ビルド成功・プッシュ済み。

```

## 2026-07-08 09:03 — gh_portal #60 Practice演習開始時のローディングインジケーター追加

- 結果: ✅ 成功

```
完了です。

実装内容:
- `Practice.tsx:209` に `const [loadingQuiz, setLoadingQuiz] = useState(false)` を追加
- `startQuiz` を `try/finally` で囲み、開始時に `setLoadingQuiz(true)`、終了時（成功・失敗問わず）に `setLoadingQuiz(false)` をセット
- `if (screen === 'quiz')` の直前に `if (loadingQuiz)` の早期リターンを追加し、CSS アニメーション付きのスピナーと「問題を読み込み中…」テキストをフルスクリーンオーバーレイで表示

これにより、テスト開始ボタンを押した瞬間からDB取得完了までの間、UIがフリーズして見える問題が解消されます。

```

## 2026-07-08 09:08 — gh_portal #61 React ErrorBoundaryの追加

- 結果: ✅ 成功

```
完了しました。

**実施内容:**

- `src/components/ErrorBoundary.tsx` を新規作成（React クラスコンポーネント）
  - 日本語フォールバック UI（アプリの CSS 変数・カードスタイルに準拠）
  - 「再試行」ボタンで状態リセット可能
  - `componentDidCatch` でコンソールにエラーログを出力
- **`Layout.tsx`** の `Outlet` 周辺に追加 → ページ単位のエラーをキャッチ、Header/TabBar は維持
- **`App.tsx`** のトップレベルにも追加 → Context 例外など全体をカバー
- ビルド成功、`git push` 済み

```

## 2026-07-08 09:15 — gh_portal #63 Onboardingフォーム途中保存の実装

- 結果: ✅ 成功

```
実装完了です。変更内容:

**`Onboarding.tsx` / `TeacherOnboarding.tsx` 共通の仕様:**

- **自動保存**: フォームの任意のフィールドが変わるたびに `localStorage` へ保存（キー: `onboarding_draft_student_<userId>` / `onboarding_draft_teacher_<userId>`）
- **復元**: コンポーネントマウント時にドラフトを読み込み、保存されていたステップと全フィールドを復元して「途中から再開」できる
- **クリーンアップ**: 送信成功後に `localStorage.removeItem` でドラフトを削除
- **耐障害性**: JSON パース失敗・ストレージ容量不足は try/catch で黙殺

```

## 2026-07-08 09:20 — gh_portal #64 React.lazyによるページ単位コード分割の導入

- 結果: ✅ 成功

```
実装完了。変更内容のまとめ：

**実装内容 (`src/App.tsx`)**
- 全19ページコンポーネントの `import { X } from '...'` を `React.lazy()` に変換
- named export 対応のため `.then(m => ({ default: m.X }))` パターンを使用
- `<AppRoutes />` を `<Suspense fallback={<LoadingScreen />}>` でラップ（既存の読み込み画面を再利用）

**効果（ビルド結果）**
- 各ページが独立チャンクに分割され、訪問したページのみが読み込まれるように
  - Practice: 223KB、MathMarkdown: 428KB、Dashboard: 101KB、Chat: 44KB など
- 初期バンドル（index.js）が 413KB に抑制（コード分割前は全ページ分が一括含まれていた）

```

## 2026-07-08 09:27 — gh_portal #65 toInitial・fmtDate等の重複ユーティリティ関数をlib/utils.tsに集約

- 結果: ✅ 成功

```
完了しました。

**実施内容まとめ：**

- `src/lib/utils.ts` を新規作成し、4つの関数をエクスポート：
  - `toInitial` — adminUtils の堅牢版（`?.trim()` + `?? '?'`）を採用
  - `fmtDate` — "YYYY-MM-DD" → "MM/DD"（Chat・Dashboard の面談日表示用）
  - `fmtDateFull` — ISO文字列 → "YYYY/MM/DD"、null安全（ProfileSheet・AdminStudents・AdminDeliverables用）
  - `fmtDateTime` — ISO文字列 → "YYYY/MM/DD HH:MM"（ProfileSheet・AdminDeliverables用）

- `adminUtils.ts` は `utils.ts` から `toInitial` を再エクスポートする形に変更し、`AdminUsers.tsx` / `AdminPayroll.tsx` 側のインポートを変更不要に

- ローカル定義を削除したファイル：`Timeline.tsx`、`Chat.tsx`、`Dashboard.tsx`、`ProfileSheet.tsx`、`AdminDeliverables.tsx`、`AdminStudents.tsx`

ビルドエラーなし、push 完了。

```

## 2026-07-08 09:31 — gh_portal #66 PillItem型定義のChat.tsxとDashboard.tsx間での重複解消

- 結果: ✅ 成功

```
完了しました。

**変更内容:**
- `src/lib/types.ts` を新規作成し、`TaskStatus` 型と `PillItem` インターフェース（Dashboard版の完全な定義）を定義
- `Dashboard.tsx` から重複する `TaskStatus` と `PillItem` の定義を削除し、`lib/types` からimport
- `Chat.tsx` から `PillItem` の定義を削除し、`lib/types` からimport
- `tsc --noEmit` で型エラーなしを確認済み

```

## 2026-07-08 09:36 — gh_portal #67 Supabase匿名キーのハードコード確認とenv変数の型安全ラッパー追加

- 結果: ✅ 成功

```
完了しました。

**変更内容:** `src/lib/supabase.ts` に `requireEnv()` ヘルパーを追加し、`VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` が未設定の場合に起動時（モジュールロード時）に明示的なエラーを投げるよう修正しました。これにより `as string` キャストで `undefined` が無言で `createClient` に渡っていた問題が解消されます。

```

## 2026-07-08 09:49 — gh_portal #68 Dashboard.tsxのインラインstyle(358箇所)をCSS変数・クラスに段階的に移行

- 結果: ✅ 成功

```
完了しました。

## 実施内容

**globals.css に追加したユーティリティクラス（140行追加）：**

| クラス群 | 用途 | 削減した重複 |
|----------|------|--------------|
| `.dashboard-stats-strip` / `.dashboard-stats-cell` / `.dashboard-stats-label` / `.dashboard-stats-value` | 4セルのサマリーストリップグリッド | 生徒・教師の両側に重複していた8セル分のインラインstyle |
| `.notice-card` + `--info / --success / --warning / --compact / --row` | 面談招待・確定・アンケート通知カード | 3枚のカードの`margin / padding / borderRadius / background / border`の重複 |
| `.notice-card__head` | カード内ヘッダー行 | 各カード内の`display:flex / gap / fontWeight / fontSize`の重複 |
| `.status-badge` + `--warning / --error / --success / --muted / --bold` | `MeetingBadge`の全5状態 | 5パターンのバッジで各10個以上のプロパティが重複 |
| `.spinner` / `.tl-empty-state` / `.tl-empty-state__msg` | ローディング・空状態 | 2箇所で重複していたローディングUI |

**既存機能への影響なし**（ビルド成功・TypeScriptエラーなし）。

```

## 2026-07-08 09:53 — gh_portal #69 Contents.tsxの動画プレイヤーをlazy importに分離

- 結果: ✅ 成功

```
完了しました。

**実施内容:**
- `src/pages/VideoDetail.tsx` を新規作成し、`videoRef` / インターバル / 進捗保存ロジックを含む `VideoDetail` コンポーネントを分離
- `Contents.tsx` で `React.lazy` + `Suspense` による動的インポートに切り替え（モーダルが `selected !== null` のときだけチャンクを読み込む）
- `ContentItem` 型を `export interface` に変更し `VideoDetail.tsx` から参照できるようにした

ビルド結果で `VideoDetail-D8iFxHki.js`（3.13 kB）が独立チャンクとして分割されたことを確認済みです。

```

## 2026-07-08 09:56 — gh_portal #70 Chat講師チャットのhandleReorder逐次awaitをPromise.allに変更

- 結果: ✅ 成功

```
完了しました。`Dashboard.tsx:137` の `handleReorder` 内で `for...of + await` による直列DB更新を `Promise.all` + `.map()` による並列実行に変更し、コミット・プッシュ済みです。複数スロットが同時に移動された場合も、全更新リクエストが並列で発火するためUIブロックが解消されます。

```

## 2026-07-08 10:03 — gh_portal #71 Onboarding・TeacherOnboardingの送信エラー時にトースト通知を追加

- 結果: ✅ 成功

```
実装完了。

**変更内容:**
- `src/components/Toast.tsx` — 新規作成。固定位置（画面上部中央）に表示、4秒後自動消去、✕ボタンで手動閉じも可能
- `src/styles/globals.css` — `.toast` / `.toast--error` / `.toast__message` / `.toast__close` と `toast-in` アニメーションを追加
- `Onboarding.tsx` / `TeacherOnboarding.tsx` — エラー発生箇所（DB失敗・タイムアウト・予期せぬエラー）で `setToastMsg(msg)` を追加し `<Toast>` をレンダリング

既存の `setError()` によるフォーム内表示は維持しつつ、スクロール位置に依存しない画面固定のトーストも同時に表示されます。

```

## 2026-07-08 10:10 — gh_portal #72 AdminUsers招待トークンの有効期限・使用済みチェックをクライアント側で表示

- 結果: ✅ 成功

```
実装完了です。

**変更内容：**

`AdminUsers.tsx` の招待モーダルに「招待履歴」セクションを追加しました。

- モーダルを開くと `invitations` テーブルから最新20件を取得・表示
- 各招待リンクに3つのステータスバッジを表示：
  - **有効**（緑）— `expires_at` が未来かつ未使用
  - **期限切れ**（グレー）— `expires_at` が過去
  - **使用済み**（青）— `used_by` が非null
- 有効なリンクのみコピーボタン表示
- 新規招待発行後に履歴を自動リフレッシュ

```

## 2026-07-08 10:15 — gh_portal #73 本番console.errorをstructured loggingサービス(Sentry等)へ置換する準備としてエラーレポートユーティリティを追加

- 結果: ✅ 成功

```
完了しました。

**実施内容:**

- `src/lib/reportError.ts` を新規作成。現在は `console.error` へのフォールスルーで動作し、将来 Sentry 等を導入する際はこの関数の中身を変更するだけで全エラー報告先を切り替えられます。
- 19箇所の `console.error` を `reportError` に置換（9ファイル）:
  - `ErrorBoundary.tsx`, `storage.ts`, `Login.tsx`, `Register.tsx`, `Onboarding.tsx`, `TeacherOnboarding.tsx`, `Practice.tsx`, `Dashboard.tsx`, `AdminJob.tsx`, `Job.tsx`
- `tsc && vite build` でビルド成功を確認後、コミット＆プッシュ済み。

```

## 2026-07-08 10:22 — gh_portal #83 AdminMessages「プレビュー/確認」ボタンのonClickハンドラ実装

- 結果: ✅ 成功

```
実装完了・push済みです。

**変更内容:**

- `AdminMessages.tsx` の `プレビュー・確認` ボタン（291行目）に `onClick={() => setShowPreview(true)}` を追加
- `showPreview` ステートを追加し、クリック時に確認モーダルを表示
- モーダルには「送信対象（全生徒/未提出者/個別選択した名前一覧）」と「メッセージ本文・文字数」を表示
- モーダル内の「確認して送信」ボタンが `handleSendStudents()` を呼び、成功時にモーダルを閉じる
- オーバーレイクリックでもキャンセル可能
- `handleSendStudents` を `Promise<boolean>` に変更し、成功/失敗を返すよう修正（既存の「LINE送信」ボタンの動作は変わらず）

```

## 2026-07-08 10:27 — gh_portal #75 不明ルートに対する404ページの追加

- 結果: ✅ 成功

```
実装完了です。

**変更内容：**
- `src/pages/NotFound.tsx` を新規作成：🔍アイコン + 「404」（プライマリカラー）+ 日本語メッセージ + 誘導ボタン（認証済みなら「タイムラインに戻る」、未認証なら「ログイン画面へ」）
- `src/App.tsx` の `path="*"` を `<RootRedirect />` から `<NotFound />` に変更

デザインはトーン・マナー準拠（`--color-primary`、`border-radius`、`btn-primary` クラス）、ビルド・push 完了しました。

```

## 2026-07-08 10:32 — gh_portal #77 AdminPayroll toggleStatusの'pending'ステータス遷移漏れ修正

- 結果: ✅ 成功

```
完了しました。

**修正内容：** `AdminPayroll.tsx:111` の1行を変更。

```typescript
// Before（バグあり）
const next: PayStatus = target.status === 'unpaid' ? 'paid' : 'unpaid'
// ↑ pending は 'unpaid' でないので 'unpaid' に遷移してしまい、paid に到達できない

// After（修正）
const next: PayStatus = target.status === 'paid' ? 'unpaid' : 'paid'
// ↑ paid 以外（unpaid・pending 両方）は paid に進む
```

これにより `pending` → `paid` の遷移が可能になり、ステータスが永久に固定されるバグが解消されます。`unpaid ⇔ paid` の既存動作も変わりません。

```

## 2026-07-08 10:42 — gh_portal #78 AdminStudents TeacherListModalの選択キーをname→idに変更

- 結果: ✅ 成功

```
完了しました。

**変更内容の要約：**

- `assignedTeachers: string[]` — 格納値を講師名 → **講師ID**に変更
- `TeacherListModal` の `selected` Set — `t.name` → `t.id` をキーに変更。チェック判定・バッジ表示・`onConfirm`コールバックすべてIDベースに統一
- 表示箇所（フッターサマリー・確認ダイアログ・生徒カード・生徒詳細画面）では `idToName()` ヘルパーでIDを名前に解決して表示
- `applyAdvanced` — `teachers[]` を受け取り、`f.teacherName`（名前文字列）からIDを逆引きして比較するよう修正
- `handleConfirmAssign` — 名前→IDの変換ステップが不要になり簡略化
- データ読み込み時の `teacherNameById` Map を削除（`myAssigns.map(a => a.teacher_id)` に簡略化）

```

## 2026-07-08 10:44 — gh_portal #79 AdminUsers toggleAdminの権限昇格操作に確認ダイアログを追加

- 結果: ✅ 成功

```
完了しました。

**変更内容：**

- `confirmTarget` state を追加。トグルボタンクリック時はDBを直接叩かず、まずダイアログを表示する
- `toggling` state を追加。DB更新中はすべてのトグルボタンを `disabled` にしてレースコンディションを防止
- ダイアログは既存の `admin-modal` スタイルを再利用し、付与時はオレンジ（primary）・剥奪時は赤（danger）ボタンで操作の重大性を区別
- `admin-btn--danger` スタイルを `globals.css` に追加

```

## 2026-07-08 10:49 — gh_portal #58 Dashboard rescheduleMaterialのN+1クエリ解消

- 結果: ✅ 成功

```
完了しました。

`rescheduleMaterial` の for ループ内逐次 `await` を `Promise.all` + `.map()` に置き換え、N回の逐次Supabaseコールを並列実行に変更しました（`Dashboard.tsx:927-930`）。ビルド・プッシュともに成功しています。

```

## 2026-07-08 11:09 — gh_portal #74 モーダル共通コンポーネント（フォーカストラップ・Escキー・aria-modal）の実装

- 結果: ✅ 成功

```
実装完了しました。

---

**実施内容まとめ:**

**`src/components/FocusTrapDialog.tsx` を新規作成し、以下の機能を実装：**
- **フォーカストラップ**: Tab/Shift+Tab でダイアログ内の要素を循環
- **Escapeキー**: 押下で `onClose` を呼び出して閉じる
- **ARIA属性**: `role="dialog"`, `aria-modal="true"`, `aria-label` を自動付与
- **createPortal**: 常に `document.body` にマウント（z-index問題を解消）
- **ネスト対応**: `activeDialogs` スタックで最前面のダイアログのみが Escape/Tab を処理
- **フォーカス復元**: アンマウント時に呼び出し元要素へフォーカスを戻す
- **`layout="sheet"` prop**: ボトムシート（overlay と dialog が兄弟要素）に対応

**適用箇所 (17モーダル):**
- Dashboard: 削除確認・志望校編集・教材追加/編集・PillDetailModal(2状態)
- Practice: タブ離脱確認・中断確認
- AdminUsers: 管理者権限確認・招待モーダル
- AdminMessages: 送信内容確認
- AdminStudents: 講師詳細・講師選択・アサイン確定確認（ネスト対応含む）
- Timeline: 投稿シート・お知らせ詳細・プロフィールミニシート（layout="sheet"）
- VideoDetail: 動画プレイヤー
- AdminJob: フィールド承認/差し戻し確認

TypeScriptエラーなし、ビルド成功、push完了。

```

## 2026-07-08 11:11 — gh_portal #76 Job.tsxフォームのcheckboxフィールドにcheckedバインディングを追加

- 結果: ✅ 成功

```
完了しました。

**修正内容** (`src/pages/Job.tsx:881-897`):
- `FieldRenderer` の `checkbox` レンダリング部分で、`<input type="checkbox" />` に `checked` と `onChange` バインディングを追加
- 複数選択に対応するため、選択値はカンマ区切り文字列 (`"optionA,optionB"`) として `formValues` state に保持
- チェック/アンチェック時に配列を更新して `onChange(next.join(','))` を呼ぶことで、送信時の `formValues` に正しく反映される

```

## 2026-07-08 11:16 — gh_portal #80 AuthContext onAuthStateChangeのTOKEN_REFRESHEDイベントでプロフィール再取得をスキップ

- 結果: ✅ 成功

```
完了しました。

**変更内容:** `AuthContext.tsx:106` の `onAuthStateChange` ハンドラに `TOKEN_REFRESHED` イベントの早期 return を追加しました。

```typescript
if (event === 'TOKEN_REFRESHED') {
  setSession(s)
  return
}
```

これにより、約1時間ごとのトークンリフレッシュ時に `fetchProfile()` によるDBクエリと `localStorage` 書き込みが発生しなくなります。セッション状態の更新（`setSession`）は引き続き行うため、JWT トークンは正常に更新されます。

```

## 2026-07-08 11:22 — gh_portal #81 ページ遷移時のdocument.title動的更新

- 結果: ✅ 成功

```
実装完了しました。

`src/App.tsx` に `PageTitleUpdater` コンポーネントを追加し、`useLocation` でルート変化を検知して `document.title` を更新するようにしました。タイトル形式は `ページ名 | 🔥 hennyujuku` で、全16ルート（ログイン・タイムライン・ダッシュボード・管理画面各種など）に対応しています。既知のパスにマッチしない場合はベースタイトル `🔥 hennyujuku` にフォールバックします。

```

## 2026-07-08 16:19 — gh_portal #82 ProfileSheet保存後のwindow.location.reload()をAuthContext状態更新に置換

- 結果: ✅ 成功

```
実装完了です。

**変更内容:**

- `AuthContext.tsx`: `refreshProfile()` 関数を追加。呼ばれると現在ユーザーの `fetchProfile()` を再実行し、`user` ステートと `localStorage` キャッシュ（isAdmin/isOwner）を更新する。インターフェースとデフォルト値にも追加。
- `ProfileSheet.tsx` (`ProfileEditView`): `handleSave()` の `window.location.reload()` を `await refreshProfile()` + `onBack()` に置換。保存後はページ全体を破棄せずに React ステートだけ更新し、メニュー画面に戻るようになった。

```

