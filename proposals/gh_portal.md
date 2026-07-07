---
app: gh_portal
app_path: /home/kokinagano/hennyujuku/gh_portal
---

# gh_portal 改善提案

- [x] 【運用/中】database.types.tsの再生成 — `supabase gen types`を実行し、コードで使用中だが型定義未反映の11テーブル（student_subjects, departments, meeting_records等）をdatabase.types.tsに追加して`(supabase as any)`キャストを全廃する <!-- id:1 done:2026-07-07T09:02 -->
- [x] 【セキュリティ/小】MeetingRecordContextのlocalStorage→DB移行 — 面談記録（MeetingRecordContext）がlocalStorageのみに保存されており、Dashboard.tsxではmeeting_recordsテーブルへの読み書きが既に実装済みなのでContextをDB参照に統一する <!-- id:2 done:2026-07-07T09:28 -->
- [x] 【セキュリティ/小】MeetingFeedbackContextのlocalStorage→DB移行 — 面談フィードバック（MeetingFeedbackContext）もlocalStorageのみだが、Dashboard.tsxではmeeting_feedbacksテーブルへのINSERTが実装済みなのでContextをDB参照に統一する <!-- id:3 done:2026-07-07T09:58 -->
- [x] 【機能/小】未使用テーブルjob_tasks/job_task_comments/job_task_readsの画面実装 — database.types.tsにタスク管理スキーマが定義済みだがどの画面からもアクセスされていないため、AdminJobまたはJob画面にタスク管理UIを追加する <!-- id:4 done:2026-07-07T08:38 -->
- [x] 【機能/小】Contents画面の書き込み機能追加 — Contents.tsxはcontent_progressのSELECTのみで視聴進捗の更新（UPDATE/UPSERT）を行っていないため、動画視聴時にwatch_pctとlast_position_secを記録する処理を追加する <!-- id:5 done:2026-07-07T10:30 -->
- [x] 【性能/小】Dashboard.tsxのクエリ分割とキャッシュ — 4316行の巨大コンポーネントで講師ダッシュボードのfetchStudents()が5テーブルを同時にPromise.allで取得しており、担当生徒数増加時に重くなるためページネーションまたはSWR的キャッシュを導入する <!-- id:6 done:2026-07-07T10:58 -->
- [x] 【運用/小】life_pattern_slotsテーブルの使途確認と整理 — database.types.tsにlife_pattern_slotsが定義されているがlife_patterns.blocksにJSONで同等データを格納しており二重管理状態なので不要なら型定義とテーブルを削除する <!-- id:7 done:2026-07-07T11:28 -->
- [x] 【セキュリティ/小】AdminMessages画面のメッセージ送信DB保存 — AdminMessages.tsxはjobs/profilesのSELECTのみでメッセージ本文のINSERTがなく、送信ロジックが未実装のため送信結果のDB永続化を追加する <!-- id:8 done:2026-07-07T12:00 -->
- [ ] 【テスト/中】画面別Supabaseクエリの統合テスト作成 — 44テーブルへの接続点がRLS等で保護されているか検証するため、各画面のCRUD操作に対してロール別（student/teacher/admin）の権限テストを作成する <!-- id:9 -->
- [x] 【UI/UX/小】get_university_rankingのRPCエラーハンドリング追加 — Dashboard.tsxのUniversityRankingPanelでsupabase.rpc呼び出しの失敗時にユーザーへのフィードバックがないため、エラー表示とリトライUIを追加する <!-- id:10 done:2026-07-07T12:28 -->
- [ ] 【運用/中】Realtime購読の一元管理 — Dashboard/Chat/Job/AdminJobで個別にsupabase.channel()を管理しており購読漏れ（メモリリーク）のリスクがあるため、useRealtimeカスタムフックで購読ライフサイクルを統一する <!-- id:11 -->
- [x] 【セキュリティ/小】tutorialDone状態のDB永続化 — completeTutorial()がlocalStorageのみに書き込んでおりDB保存されないため、ブラウザデータ消去で状態がリセットされる問題をprofilesテーブルへの書き込みに修正する <!-- id:12 done:2026-07-07T13:01 -->
- [x] 【機能/中】Chat.tsx講師ビューの生徒リストDB化 — 講師側チャットの生徒リスト（STUDENTS定数）が完全にハードコードされており、teacher_student_assignmentsテーブルから実データを取得するよう置き換える <!-- id:13 done:2026-07-07T13:32 -->
- [x] 【機能/中】Chat.txチャンネル一覧のDB化 — CHANNELS定数がハードコードされており、chat_roomsテーブルのtype='channel'から動的に取得するよう変更する <!-- id:14 done:2026-07-07T14:02 -->
- [x] 【UI/UX/小】GoalPanelの受験日表示をDBから取得 — Dashboard.tsx:1560で「2027-01-23（土）共通テスト」がハードコードされており、student_profiles.exam_dateから動的に表示すべき <!-- id:15 done:2026-07-07T14:32 -->
- [ ] 【性能/小】LifePatternContextの楽観的更新ロールバック実装 — addPatternで仮IDによる楽観的更新を行うがDB insert失敗時にロールバックされず、UIに存在しないパターンが残り続ける問題を修正する <!-- id:16 -->
- [x] 【UI/UX/小】Dashboard生徒画面のスケジュール読み込み中表示追加 — pills配列が空の初期状態と実際にスケジュールがない状態が区別できず、ローディングインジケーターが表示されない問題を修正する <!-- id:17 done:2026-07-07T15:03 -->
- [x] 【セキュリティ/小】saveLifeSlotsToDbのdelete→insert原子性確保 — Dashboard.tsx:137-162でdelete成功後にinsertが失敗するとスロットデータが消失するため、エラーチェックと失敗時の通知を追加する <!-- id:18 done:2026-07-07T15:33 -->
- [x] 【UI/UX/小】Timeline.tsxいいねトグルの失敗時ロールバック追加 — toggleLikeで楽観的更新後にDB同期が失敗してもUIが戻らない問題を修正し、エラー時に元の状態に復元する <!-- id:19 done:2026-07-07T16:03 -->
- [x] 【機能/中】Practice.tsxレーダーチャート・成績推移のDB化 — RADAR_SCORESとSCORE_HISTORYが完全にハードコードされており、auto_score_resultsテーブルの実データから集計表示するよう置き換える <!-- id:20 -->
- [ ] 【UI/UX/小】AssignNotification承諾・相談フローのエラーハンドリング追加 — handleAccept/handleConsultで複数のDB操作（update→insert→insert）を順次実行するが、途中失敗時にユーザーへのフィードバックがなくUIだけ進む問題を修正する <!-- id:21 -->
- [ ] 【機能/小】AdminStudents講師割り当て変更のエラーハンドリング追加 — upsert/deleteによる担当講師変更（AdminStudents.tsx:942-948）でエラーを無視しておりUI上は成功に見えるが実際にはDB反映されていない可能性がある問題を修正する <!-- id:22 -->
