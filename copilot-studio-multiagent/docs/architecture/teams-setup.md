# Microsoft Teams チャンネル設定

## チーム情報

| 項目 | 設定値 |
|---|---|
| チーム名 | AI-Org |
| 種別 | プライベートチーム |
| メンバー | CEO（オーナー）＋ Power Automate サービスアカウント |

---

## チャンネル構成

| チャンネル名 | 用途 | 投稿者 | 主な受信者 |
|---|---|---|---|
| **Inbox** | CEOが思いついたことを何でも放り込む場所 | CEO（手動） | Power Automate（自動読み取り） |
| **Morning Standup** | 毎朝07:00の自動進捗レポート受信 | Power Automate | CEO |
| **Escalation** | P0タスク・要承認事項の緊急通知 | Power Automate | CEO（通知必須） |
| **Agent Logs** | 各エージェントの実行ログ・完了報告 | Power Automate | CEO（モニタリング用） |
| **Weekly Brief** | 週次ビジネスブリーフィングの受信 | Power Automate | CEO |

---

## Inbox チャンネル 使用ルール（CEO向け）

Inboxチャンネルには形式不問で投稿してよい。  
Power Automateが自動的に分類・タスク化する。

**投稿例:**
```
動画ネタ: AIエージェントで一人法人運営する方法、シリーズ化したい

→ Power AutomateがSharePoint /Inbox/ に保存し
   Plannerに [コンテンツ] タスクを自動起票する
```

```
バグ: ダッシュボードのグラフが更新されない。Chrome最新版で再現

→ Power AutomateがSharePoint /Inbox/ に保存し
   Plannerに [エンジニア] タスクを自動起票する
```

```
○○社から協業打診のメールが来た。以下が本文…

→ Power AutomateがSharePoint /Inbox/ に保存し
   Plannerに [ビジネス] タスクを自動起票する
```

---

## Escalation チャンネル 通知フォーマット

```
⚠️ P0エスカレーション - CEOの判断が必要です

タスク: [ビジネス] ○○社コラボ方針確認
優先度: P0（本日中）
ブロック理由: ブランドポリシー上の判断基準が未定義のため自動判断不可

▶ Planner タスク: [リンク]
▶ 詳細（SharePoint）: [リンク]

このメッセージに返信するか、Plannerタスクのメモに指示を記入してください。
```

---

## Power Automate コネクタ設定

| コネクタ | 使用目的 |
|---|---|
| Microsoft Teams | チャンネルメッセージ取得・投稿 |
| SharePoint | ファイル作成・更新・読み取り |
| Microsoft Planner | タスク作成・更新・取得 |
| Azure OpenAI | タスク分類・サマリー生成 |
| AI Builder | （オプション）ドキュメント分析 |

---

## モバイル設定推奨（CEO向け）

1. Teams モバイルアプリで **Escalation チャンネルの通知をON**（重要度：高）
2. **Morning Standup チャンネルの通知** を毎朝07:05に確認する習慣をつける
3. **Inbox チャンネル** はウィジェットをホーム画面に追加して素早く投稿できるようにする
