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

