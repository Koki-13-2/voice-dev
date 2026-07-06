---
app: gh_portal
app_path: /home/kokinagano/hennyujuku/gh_portal
---

# gh_portal 改善提案

- [x] 【運用/中】database.types.tsの再生成 — `supabase gen types`を実行し、コードで使用中だが型定義未反映の11テーブル（student_subjects, departments, meeting_records等）をdatabase.types.tsに追加して`(supabase as any)`キャストを全廃する <!-- id:1 -->
- [x] 【セキュリティ/小】MeetingRecordContextのlocalStorage→DB移行 — 面談記録（MeetingRecordContext）がlocalStorageのみに保存されており、Dashboard.tsxではmeeting_recordsテーブルへの読み書きが既に実装済みなのでContextをDB参照に統一する <!-- id:2 -->
- [x] 【セキュリティ/小】MeetingFeedbackContextのlocalStorage→DB移行 — 面談フィードバック（MeetingFeedbackContext）もlocalStorageのみだが、Dashboard.tsxではmeeting_feedbacksテーブルへのINSERTが実装済みなのでContextをDB参照に統一する <!-- id:3 -->
- [x] 【機能/小】未使用テーブルjob_tasks/job_task_comments/job_task_readsの画面実装 — database.types.tsにタスク管理スキーマが定義済みだがどの画面からもアクセスされていないため、AdminJobまたはJob画面にタスク管理UIを追加する <!-- id:4 done:2026-07-07T08:38 -->
- [x] 【機能/小】Contents画面の書き込み機能追加 — Contents.tsxはcontent_progressのSELECTのみで視聴進捗の更新（UPDATE/UPSERT）を行っていないため、動画視聴時にwatch_pctとlast_position_secを記録する処理を追加する <!-- id:5 -->
- [x] 【性能/小】Dashboard.tsxのクエリ分割とキャッシュ — 4316行の巨大コンポーネントで講師ダッシュボードのfetchStudents()が5テーブルを同時にPromise.allで取得しており、担当生徒数増加時に重くなるためページネーションまたはSWR的キャッシュを導入する <!-- id:6 -->
- [x] 【運用/小】life_pattern_slotsテーブルの使途確認と整理 — database.types.tsにlife_pattern_slotsが定義されているがlife_patterns.blocksにJSONで同等データを格納しており二重管理状態なので不要なら型定義とテーブルを削除する <!-- id:7 -->
- [x] 【セキュリティ/小】AdminMessages画面のメッセージ送信DB保存 — AdminMessages.tsxはjobs/profilesのSELECTのみでメッセージ本文のINSERTがなく、送信ロジックが未実装のため送信結果のDB永続化を追加する <!-- id:8 -->
- [ ] 【テスト/中】画面別Supabaseクエリの統合テスト作成 — 44テーブルへの接続点がRLS等で保護されているか検証するため、各画面のCRUD操作に対してロール別（student/teacher/admin）の権限テストを作成する <!-- id:9 -->
- [x] 【UI/UX/小】get_university_rankingのRPCエラーハンドリング追加 — Dashboard.tsxのUniversityRankingPanelでsupabase.rpc呼び出しの失敗時にユーザーへのフィードバックがないため、エラー表示とリトライUIを追加する <!-- id:10 -->
- [x] 【運用/中】Realtime購読の一元管理 — Dashboard/Chat/Job/AdminJobで個別にsupabase.channel()を管理しており購読漏れ（メモリリーク）のリスクがあるため、useRealtimeカスタムフックで購読ライフサイクルを統一する <!-- id:11 -->
