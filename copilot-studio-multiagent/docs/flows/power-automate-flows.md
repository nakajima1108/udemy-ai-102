# Power Automate フロー設計書

## フロー一覧

| フロー名 | トリガー種別 | 主なアクション | 担当エージェント |
|---|---|---|---|
| PA-InboxCapture | Teamsメッセージ投稿 | SP保存 → Plannerタスク起票 | タスクディパッチ |
| PA-MorningStandup | スケジュール（毎朝07:00） | Planner取得 → AI生成 → Teams送信 | タスクディパッチ |
| PA-ContentReview | Plannerタスク更新（#content/New→InProgress） | SPファイル読込 → エージェント連鎖呼び出し | コンテンツDr→各エージェント |
| PA-NightlyQARun | スケジュール（毎日02:00） | Planner取得 → QAエージェント呼び出し → レポート保存 | QA |
| PA-WeeklyBrief | スケジュール（毎週月曜06:30） | Planner/SP収集 → ビジネスストラテジー呼び出し → Teams送信 | ビジネスストラテジー |
| PA-ArchiveCleanup | スケジュール（毎週日曜02:00） | Planner/SP収集 → アーカイブ処理 | ローカルサポート |
| PA-EscalationNotify | Plannerタスク更新（P0ラベル付与時） | Teams [Escalation] に即時通知 | タスクディパッチ |

---

## フロー詳細設計

---

### 1. PA-InboxCapture（Inboxキャプチャ）

**目的**: TEAMSのInboxチャンネルへの投稿を受け取り、SharePointに保存してPlannerに起票する

```
[トリガー]
Microsoft Teams: 「新しいチャンネルメッセージが投稿された」
  - チーム: AI-Org
  - チャンネル: Inbox

[アクション1] SharePointファイル作成
SharePoint: ファイルの作成
  - サイト: AI-Org-Intranet
  - フォルダーパス: /Inbox/
  - ファイル名: @{formatDateTime(utcNow(),'yyyy-MM-dd_HHmmss')}_inbox.md
  - ファイルコンテンツ:
    ---
    received_at: @{utcNow()}
    from: CEO
    ---
    @{triggerBody()?['body']['content']}

[アクション2] Azure OpenAI でタスク分類
HTTP: POST
  - URI: [Azure OpenAI エンドポイント]
  - ボディ: 
    {
      "messages": [
        {
          "role": "system",
          "content": "以下のテキストを読んでJSON形式でタスク分類してください。\ncategory: engineering/content/business/infra\npriority: P0/P1/P2\nsummary: 50文字以内のタスクタイトル\nassignee: タスクディパッチ/コンテンツディレクター/テックリード/マーケティングディレクター/パートナーシップマネージャー/リーガルレビュー/ビジネスストラテジー/ローカルサポート"
        },
        {
          "role": "user",
          "content": "@{triggerBody()?['body']['content']}"
        }
      ],
      "model": "gpt-4o-mini"
    }

[アクション3] Plannerタスク作成
Microsoft Planner: タスクを作成する
  - プラン: AI-Org タスクボード
  - バケット: New
  - タイトル: [@{body('Parse_Classification')?['category']}] @{body('Parse_Classification')?['summary']}
  - 担当者: @{body('Parse_Classification')?['assignee']}
  - 期日: @{addDays(utcNow(), if(equals(body('Parse_Classification')?['priority'],'P0'),0,if(equals(body('Parse_Classification')?['priority'],'P1'),7,14)))}
  - メモ: SharePoint URL: @{outputs('Create_SP_File')?['body/ServerRelativeUrl']}

[アクション4] P0判定
条件: body('Parse_Classification')?['priority'] == 'P0'
  はい → PA-EscalationNotify を呼び出す
  いいえ → 終了
```

---

### 2. PA-MorningStandup（モーニングスタンドアップ）

**目的**: 毎朝07:00にPlannerの状況を集約してTeamsに送信する

```
[トリガー]
スケジュール: 毎日 07:00 JST（22:00 UTC）

[アクション1] Plannerタスク取得（3種）
Microsoft Planner: タスクの取得
  - プラン: AI-Org タスクボード
  実行1: バケット=Done、フィルタ: 完了日が昨日
  実行2: バケット=In Progress
  実行3: バケット=Blocked

[アクション2] Azure OpenAI でサマリー生成
HTTP: POST
  - モデル: gpt-4o-mini
  - プロンプト: 以下のPlannerデータからモーニングスタンドアップレポートを生成してください
    Done（昨日完了）: @{variables('DoneTasks')}
    In Progress（対応中）: @{variables('InProgressTasks')}
    Blocked（停止中）: @{variables('BlockedTasks')}

[アクション3] Teams送信
Microsoft Teams: メッセージの投稿
  - チーム: AI-Org
  - チャンネル: Morning Standup
  - メッセージ: @{body('Generate_Standup')?['choices'][0]['message']['content']}

[アクション4] P0タスク存在確認
条件: Blocked内にP0ラベルのタスクが存在する
  はい → Teams [Escalation] にも別途送信
```

---

### 3. PA-ContentReview（コンテンツレビューパイプライン）

**目的**: コンテンツタスクが起票されたとき、4エージェントの連鎖レビューを実行する

```
[トリガー]
Microsoft Planner: タスクが更新された
  - プラン: AI-Org タスクボード
  - 条件: バケットが「New」→「In Progress」 かつ ラベルに「#content」が含まれる

[アクション1] タスク詳細取得
Planner からメモ欄のSharePoint URLを取得し草稿ファイルを読み込む

[アクション2] コンテンツディレクター呼び出し
Copilot Studio エージェント呼び出し（HTTP）
  - エージェント: Content Director
  - 入力: 草稿テキスト + タスクID

[アクション3] ブランドボイス呼び出し（コンテンツDrの出力を渡す）
Copilot Studio エージェント呼び出し
  - エージェント: Brand Voice
  - 入力: /AI-Handoff/content-director/[タスクID].md の内容

[アクション4] ルート構図呼び出し
Copilot Studio エージェント呼び出し
  - エージェント: Root Cause
  - 入力: /AI-Handoff/brand-voice/[タスクID].md の内容

[アクション5] アンチAIスロップ呼び出し
Copilot Studio エージェント呼び出し
  - エージェント: Anti-AI-Slop
  - 入力: /AI-Handoff/root-cause/[タスクID].md の内容

[アクション6] 最終稿をReportsに保存
SharePoint: /Reports/content/[タスクID]_final.md に保存

[アクション7] Plannerタスクを Done に更新
Planner: タスクの更新
  - バケット: Done
  - メモに最終稿URLを追記

[アクション8] MAJOR_RESTRUCTURE 検出時のみ
条件: アンチAIスロップの出力にMAJOR_RESTRUCTUREが含まれる
  はい → Plannerを Blocked に更新 ＋ Escalation通知
```

---

### 4. PA-NightlyQARun（夜間QAラン）

**目的**: 毎日02:00に当日完了したエンジニアリングタスクを自動QAする

```
[トリガー]
スケジュール: 毎日 02:00 JST（17:00 UTC）

[アクション1] 当日Done化したタスクを取得
Planner: バケット=Done、ラベル=#engineering、完了日=今日のタスク一覧

[アクション2] 各タスクについてQAエージェント呼び出し
Apply to each ループ:
  - /AI-Handoff/[frontend or backend]/[タスクID].md を読み込む
  - QAエージェントを呼び出す
  - 結果を /Reports/qa-results/[日付]/[タスクID].md に保存

[アクション3] FAILタスクの処理
条件: QA結果にFAILが含まれる
  はい →
    Plannerタスクを Done → Blocked に戻す
    タスクメモにQA失敗理由を追記
    Teams [Agent Logs] に通知

[アクション4] 夜間QAサマリーをTeamsに送信
Teams [Agent Logs]: QAラン完了レポートを送信
  - 対象タスク数・PASS数・FAIL数
```

---

### 5. PA-WeeklyBrief（週次ブリーフィング）

**目的**: 毎週月曜06:30にビジネス状況を集約してCEOに報告する

```
[トリガー]
スケジュール: 毎週月曜 06:30 JST

[アクション1] 先週の全タスク収集
Planner: 先週(月〜日)にDoneになったタスク一覧 + Blocked継続タスク一覧

[アクション2] 各エージェントのHandoffログ収集
SharePoint: /AI-Handoff/ 配下の先週更新ファイル一覧取得

[アクション3] ビジネスストラテジー エージェント呼び出し
入力: 収集した全データ
出力: 週次ブリーフィングMarkdown

[アクション4] /Reports/weekly-business-brief/ に保存

[アクション5] Teams [Weekly Brief] チャンネルに投稿
```

---

### 6. PA-ArchiveCleanup（定期アーカイブ）

**目的**: 毎週日曜02:00に古いタスク・ファイルをアーカイブする

```
[トリガー]
スケジュール: 毎週日曜 02:00 JST

[アクション1] Planner Done タスク（7日以上前）を取得
[アクション2] タスクをMarkdownにエクスポートして /Archive/YYYY-MM/ に保存
[アクション3] Plannerからタスクを削除
[アクション4] SharePoint /Inbox/ の処理済みファイルを /Archive/Inbox/YYYY-MM/ に移動
[アクション5] SharePoint /AI-Handoff/ の30日以上前のファイルを /Archive/Handoff/YYYY-MM/ に移動
[アクション6] ヘルスレポートを /Reports/ に保存
[アクション7] Teams [Agent Logs] にメンテナンス完了報告
```

---

## Copilot Studio エージェント呼び出し方法（HTTP）

Copilot Studio のエージェントはDirect Line APIで呼び出す：

```
POST https://directline.botframework.com/v3/directline/conversations/{conversationId}/activities
Authorization: Bearer {DirectLineSecret}
Content-Type: application/json

{
  "type": "message",
  "from": { "id": "power-automate" },
  "text": "[エージェントへの指示 + 入力データ]"
}
```

### Power Automate でのカスタムコネクタ設定

1. Copilot Studio でエージェントを発行（チャンネル: Direct Line）
2. Direct Line シークレットを取得
3. Power Automate でカスタムコネクタを作成
4. Key Vault に Direct Line シークレットを格納して参照

---

## 環境変数（Power Automate 変数）

| 変数名 | 値 | 説明 |
|---|---|---|
| SP_SITE_URL | https://[テナント].sharepoint.com/sites/ai-org-intranet | SharePoint サイトURL |
| PLANNER_PLAN_ID | [PlannerプランID] | AI-Orgタスクボードのプランから取得 |
| TEAMS_TEAM_ID | [TeamsチームID] | AI-OrgチームID |
| AOAI_ENDPOINT | [Azure OpenAIエンドポイント] | Azure OpenAI リソースURL |
| AOAI_KEY | [Key Vaultシークレット参照] | Azure OpenAI APIキー |
| DL_SECRET_CONTENT | [Key Vaultシークレット参照] | コンテンツDrのDirect Lineシークレット |
| DL_SECRET_INFRA | [Key Vaultシークレット参照] | タスクディパッチのDirect Lineシークレット |
