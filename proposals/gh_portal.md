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
- [ ] 【運用/中】Realtime購読の一元管理 — Dashboard/Chat/Job/AdminJobで個別にsupabase.channel()を管理しており購読漏れ（メモリリーク）のリスクがあるため、useRealtimeカスタムフックで購読ライフサイクルを統一する <!-- id:11 done:2026-07-07T18:46 -->
- [x] 【セキュリティ/小】tutorialDone状態のDB永続化 — completeTutorial()がlocalStorageのみに書き込んでおりDB保存されないため、ブラウザデータ消去で状態がリセットされる問題をprofilesテーブルへの書き込みに修正する <!-- id:12 done:2026-07-07T13:01 -->
- [x] 【機能/中】Chat.tsx講師ビューの生徒リストDB化 — 講師側チャットの生徒リスト（STUDENTS定数）が完全にハードコードされており、teacher_student_assignmentsテーブルから実データを取得するよう置き換える <!-- id:13 done:2026-07-07T13:32 -->
- [x] 【機能/中】Chat.txチャンネル一覧のDB化 — CHANNELS定数がハードコードされており、chat_roomsテーブルのtype='channel'から動的に取得するよう変更する <!-- id:14 done:2026-07-07T14:02 -->
- [x] 【UI/UX/小】GoalPanelの受験日表示をDBから取得 — Dashboard.tsx:1560で「2027-01-23（土）共通テスト」がハードコードされており、student_profiles.exam_dateから動的に表示すべき <!-- id:15 done:2026-07-07T14:32 -->
- [x] 【性能/小】LifePatternContextの楽観的更新ロールバック実装 — addPatternで仮IDによる楽観的更新を行うがDB insert失敗時にロールバックされず、UIに存在しないパターンが残り続ける問題を修正する <!-- id:16 done:2026-07-07T18:39 -->
- [x] 【UI/UX/小】Dashboard生徒画面のスケジュール読み込み中表示追加 — pills配列が空の初期状態と実際にスケジュールがない状態が区別できず、ローディングインジケーターが表示されない問題を修正する <!-- id:17 done:2026-07-07T15:03 -->
- [x] 【セキュリティ/小】saveLifeSlotsToDbのdelete→insert原子性確保 — Dashboard.tsx:137-162でdelete成功後にinsertが失敗するとスロットデータが消失するため、エラーチェックと失敗時の通知を追加する <!-- id:18 done:2026-07-07T15:33 -->
- [x] 【UI/UX/小】Timeline.tsxいいねトグルの失敗時ロールバック追加 — toggleLikeで楽観的更新後にDB同期が失敗してもUIが戻らない問題を修正し、エラー時に元の状態に復元する <!-- id:19 done:2026-07-07T16:03 -->
- [x] 【機能/中】Practice.tsxレーダーチャート・成績推移のDB化 — RADAR_SCORESとSCORE_HISTORYが完全にハードコードされており、auto_score_resultsテーブルの実データから集計表示するよう置き換える <!-- id:20 done:2026-07-07T16:39 -->
- [x] 【UI/UX/小】AssignNotification承諾・相談フローのエラーハンドリング追加 — handleAccept/handleConsultで複数のDB操作（update→insert→insert）を順次実行するが、途中失敗時にユーザーへのフィードバックがなくUIだけ進む問題を修正する <!-- id:21 done:2026-07-07T18:46 -->
- [x] 【機能/小】AdminStudents講師割り当て変更のエラーハンドリング追加 — upsert/deleteによる担当講師変更（AdminStudents.tsx:942-948）でエラーを無視しておりUI上は成功に見えるが実際にはDB反映されていない可能性がある問題を修正する <!-- id:22 done:2026-07-07T18:50 -->
- [x] 【機能/中】Dashboard学習統計（studyStreak・weeklyStudyHours等）のDB集計 — MOCK_STUDENT_STATSの4指標が常時0のままで、daily_schedule_slotsやauto_score_resultsの実績データから算出すべき <!-- id:23 done:2026-07-07T18:58 -->
- [x] 【機能/小】Chat生徒ビューの担当講師一覧をteacher_student_assignmentsから取得 — ASSIGNED_TEACHERSがハードコードされ実際のDB担当講師情報と未接続 <!-- id:24 done:2026-07-07T19:02 -->
- [x] 【機能/中】Chat AIルームのメッセージDB永続化 — AI_ROOMSとAIチャット応答が全てローカルstateで、リロード・端末変更時に全履歴が消失する <!-- id:25 done:2026-07-07T19:12 -->
- [x] 【機能/小】Chat面談招待モーダルの生徒スケジュールをdaily_schedule_slotsから取得 — STUDENT_PILLSがハードコードで生徒の実際のスケジュールと無関係な空き時間が表示される <!-- id:26 done:2026-07-07T19:15 -->
- [x] 【機能/小】room_members.last_read_atを用いたチャット未読バッジの実装 — DBにlast_read_atカラムが存在するが未使用で未読表示がモックデータに依存している <!-- id:27 done:2026-07-07T19:23 -->
- [x] 【機能/小】Practice連続学習日数をtest_submissions提出日から動的算出 — PracticeHomeバナーの「連続学習 5日」が固定リテラルで実際の学習記録と未接続 <!-- id:28 done:2026-07-07T19:25 -->
- [x] 【機能/小】Practice添削フィードバック未読数をcorrections.is_read_by_studentから集計 — unreadCountが0固定でDBのis_read_by_studentカラムが画面側で一切参照・更新されていない <!-- id:29 -->
- [x] 【機能/中】Timelineコメントいいねのテーブル新設とDB永続化 — toggleReplyLikeがローカルstate更新のみで対応DBテーブルが未定義のためリロードでいいね状態が消える <!-- id:30 -->
- [x] 【機能/小】Timeline投稿の画像添付UI実装 — posts.image_urlsカラムがDBに存在するが投稿作成UIに画像アップロード機能がなく常時null <!-- id:31 -->
- [x] 【UI・UX/小】announcements.body詳細表示の追加 — お知らせバナーがtitleのみ表示でbodyカラムの本文が閲覧不可 <!-- id:32 -->
- [x] 【UI・UX/小】ProfileSheet編集画面のフィールド拡充 — ProfileEditViewがdisplay_nameと電話番号のみ編集可でOnboardingで登録した性別・生年月日・住所等がプロフィールから変更できない <!-- id:33 -->
- [ ] 【機能/中】Chat AIルームのsetTimeout擬似応答をOpenAI API呼び出しに置換 — AI_SENDER・QUIZ_BANKをローカル定数で持つのをやめ、@AIメッセージ送信時にEdge Function経由でOpenAI APIを呼び出し実際のAI応答を返す <!-- id:34 -->
- [x] 【機能/小】Practice演習問題QUESTIONSのDB化 — src/pages/Practice.tsx L149のハードコード2問を、exercise_questionsテーブルを新設しtest_questionsと同様にSupabaseから取得する <!-- id:35 -->
- [x] 【機能/小】Practice・TeacherPracticeのハードコード日付をnew Date()に修正 — Practice.tsx L981の`new Date('2026-04-16')`とTeacherPractice.tsx L147の`new Date('2026-04-14')`を現在日付に置換する <!-- id:36 -->
- [x] 【機能/中】Practice PdfViewerとTeacherPractice PdfPaneを実PDF表示に置換 — プレースホルダーのグレーボックスをSupabase StorageのPDF URLを取得しreact-pdfまたはiframeで実ファイルを表示するコンポーネントに差し替える <!-- id:37 -->
- [x] 【機能/小】Dashboard GoalPanelのガントチャート日付範囲を動的算出 — CHART_START/CHART_END/CHART_MONTHSの固定値をstudent_profilesのexam_dateと教材の開始日・終了日から自動算出する <!-- id:38 -->
- [ ] 【機能/小】Dashboard講師ビューの生徒カードrecentRate・weeklyStudyHours・studyStreakをDB集計 — fetchStudentsでゼロ固定の3フィールドをtest_submissionsとdaily_schedule_slotsから実値を算出して表示する <!-- id:39 -->
- [ ] 【機能/小】Dashboard講師ビューのlastLoginをauth.usersのlast_sign_in_atから取得 — L3031で空文字固定のlastLoginフィールドをSupabase Authのメタデータから取得して表示する <!-- id:40 -->
- [ ] 【機能/中】AdminMessages個別生徒選択のSupabase接続実装 — L152のスタブ表示を実際のprofilesテーブルから生徒一覧を取得するピッカーUIに差し替え、選択した生徒にメッセージを送信可能にする <!-- id:41 -->
- [ ] 【機能/小】Dashboard死コードTODAY_PILLSの削除 — L29-37の未使用定数TODAY_PILLSを削除してコードの見通しを改善する <!-- id:42 -->
- [ ] 【運用/小】Job.tsx MOCK_JOBSフォールバックの削除とログイン必須化 — セッション未認証時にモックデータを表示する分岐を削除し、未ログイン時はログイン画面へリダイレクトする <!-- id:43 -->
