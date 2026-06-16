# SharePoint Online 構造設計

## サイト情報

| 項目 | 設定値 |
|---|---|
| サイト名 | AI-Org-Intranet |
| サイト種別 | チームサイト |
| URL例 | https://[テナント].sharepoint.com/sites/ai-org-intranet |
| アクセス権 | CEO（オーナー）＋ Power Automate サービスアカウント（メンバー） |

---

## ライブラリ・フォルダ構成

```
AI-Org-Intranet（SharePointサイト）
│
├── Context/                        ← 文脈エンジン（全エージェントが読み込む）
│   ├── Philosophy.md               ← 会社の哲学・価値観・ミッション
│   ├── Identity.md                 ← CEOの職歴・専門性・人格定義
│   ├── TechnicalSetup.md           ← 使用ツール・技術スタック・機材環境
│   └── VisualDesign.md             ← ブランドカラー・フォント・デザインルール
│
├── Inbox/                          ← CEOからの入力受信箱（Teams連動）
│   └── YYYY-MM-DD_[タイトル].md    ← 自動作成（Power Automateが日付付きで保存）
│
├── Projects/                       ← 進行中プロジェクト
│   └── [プロジェクト名]/
│       ├── brief.md                ← プロジェクト概要
│       ├── tasks.md                ← タスク一覧（Plannerと同期）
│       └── assets/                 ← 関連ファイル
│
├── Ideas/                          ← アイデアストック
│   └── YYYY-MM-DD_[アイデア名].md
│
├── Resources/                      ← 一次資料・参考リソース
│   └── [カテゴリ名]/
│
├── AI-Handoff/                     ← エージェント間引き継ぎ書
│   ├── task-dispatch/              ← タスクディパッチの出力
│   ├── content-director/           ← コンテンツDrの出力
│   ├── brand-voice/                ← ブランドボイスの出力
│   ├── root-cause/                 ← ルート構図の出力
│   ├── anti-ai-slop/               ← アンチAIスロップの出力
│   ├── tech-lead/                  ← テックリードの出力
│   ├── engineer-director/          ← エンジニアDrの出力
│   ├── frontend/                   ← フロントエンドの出力
│   ├── backend/                    ← バックエンドの出力
│   ├── qa/                         ← QAの出力・テスト結果
│   ├── marketing-director/         ← マーケティングDrの出力
│   ├── business-strategy/          ← ビジネスストラテジーの出力
│   ├── partnership-manager/        ← パートナーシップMgrの出力
│   └── legal-review/               ← リーガルレビューの出力
│
├── Reports/                        ← 自動生成レポート保存先
│   ├── morning-standup/            ← 日次モーニングレポート
│   ├── weekly-business-brief/      ← 週次ビジネスブリーフィング
│   └── qa-results/                 ← QA実行結果ログ
│
└── Archive/                        ← 完了済みタスク・古いファイルの格納先
    └── YYYY-MM/
```

---

## 各Contextファイルのテンプレート

### Philosophy.md（会社の哲学）

```markdown
# 会社の哲学・価値観

## ミッション
[例: テクノロジーで個人の生産性を10倍にする]

## 核心的価値観
- **誠実さ**: 誇大広告をせず、実際に役立つものだけを発信する
- **深さ**: 表面的なハウツーより、本質的な原理原則を重視する
- **自律性**: 人に依存せず、仕組みで動く組織を目指す

## コンテンツポリシー
- [発信しないこと: ○○○]
- [必ず含めること: ○○○]
- [語り口のトーン: ○○○]

## 断るべき案件の基準
- [例: 誇大広告・根拠のない主張を含む製品]
- [例: 視聴者の課題解決に繋がらない純粋な宣伝]
```

### Identity.md（CEOプロフィール）

```markdown
# CEOプロフィール・Identity

## 職歴サマリー
[例: シリコンバレー17年。○○社でエンジニア→○○社でPM→現在独立]

## 専門領域
- [例: AIプロダクト開発]
- [例: スタートアップ組織設計]

## 語り口・文体の特徴
- [例: 専門用語を使うが必ず平易な言葉で補足する]
- [例: 体験談・具体例から入り、抽象論で締める]
- [例: 絶対に使わない表現: 「革命的」「ゲームチェンジャー」「〜してみました」]

## AIエージェントへの指示
あなたは上記の人物の代理として動作します。
この人物ならどう表現するか、どう判断するかを常に基準にしてください。
```

### TechnicalSetup.md（技術環境）

```markdown
# 技術スタック・機材環境

## 開発環境
- OS: [例: macOS Sonoma]
- IDE: [例: VS Code + GitHub Copilot]
- バージョン管理: GitHub

## Microsoft 365 環境
- テナント: [テナント名]
- Copilot Studio: [プラン]
- Power Automate: [プラン]
- SharePoint: [URL]

## AIツール
- Copilot Studio エージェント: 本システム
- Azure OpenAI: GPT-4o（メイン）/ GPT-4o-mini（定型処理）

## デプロイ先
- [例: Webサイト URL]
- [例: Teams チャンネル]
```

### VisualDesign.md（ブランドデザイン）

```markdown
# ブランド ビジュアルデザインルール

## カラーパレット
- Primary: #[カラーコード]
- Secondary: #[カラーコード]
- Background: #[カラーコード]
- Text: #[カラーコード]

## フォント
- 見出し: [フォント名]
- 本文: [フォント名]

## アイコン・ロゴ使用ルール
- [例: ロゴの最小サイズは32px]
- [例: 背景色による使い分け]

## サムネイルの共通ルール
- [例: 必ずCEOの顔写真を左側に配置]
- [例: テキストは右側、最大3行]
- [例: 背景は必ずブランドカラーのグラデーション]
```

---

## Power Automate との連携方法

### Teams → SharePoint /Inbox/ への自動保存フロー

```
トリガー: Teams [Inbox チャンネル] にメッセージ投稿
  ↓
SharePoint /Inbox/ に Markdown ファイルを作成
  ファイル名: {タイムスタンプ}_{メッセージ先頭20文字}.md
  内容: CEOのメッセージ全文
  ↓
Planner に「Inbox新着」タスクを自動起票
  タイトル: [Inbox] {メッセージ先頭50文字}
  バケット: New（未アサイン）
  ラベル: #infra
```

### SharePoint 権限設定

| ライブラリ | 読み取り | 書き込み |
|---|---|---|
| /Context/ | 全エージェント | CEO（手動）のみ |
| /Inbox/ | タスクディパッチ | Power Automate のみ |
| /Projects/ | 全エージェント | 担当エージェント＋CEO |
| /AI-Handoff/ | 全エージェント | 各エージェント（自分のフォルダのみ） |
| /Reports/ | CEO | Power Automate のみ |
| /Archive/ | CEO | ローカルサポートのみ |
