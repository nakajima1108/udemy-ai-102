# AIエージェント組織システム
## Microsoft Copilot Studio × Power Platform 実装

シリコンバレー型の組織運営モデルを、MicrosoftのCopilot Studio・Power Automate・SharePoint・Teamsで実現するマルチエージェントシステムの設計ドキュメント一式です。

---

## ドキュメント構成

```
copilot-studio-multiagent/
│
├── README.md                          ← このファイル
│
├── docs/
│   ├── architecture/
│   │   ├── overview.md               ← 全体設計・3層アーキテクチャ・実装ロードマップ
│   │   ├── sharepoint-structure.md   ← SharePointフォルダ構成・Contextテンプレート
│   │   ├── planner-setup.md          ← Plannerボード設定・タスクルール・自動化フロー
│   │   └── teams-setup.md            ← Teamsチャンネル設定・通知フォーマット
│   │
│   └── flows/
│       └── power-automate-flows.md   ← 全Power Automateフローの詳細設計
│
└── agents/
    ├── infrastructure/
    │   ├── task-dispatch.md           ← タスクディパッチ Instructions
    │   └── local-support.md          ← ローカルサポート Instructions
    │
    ├── engineering/
    │   ├── tech-lead.md              ← テックリード Instructions
    │   ├── engineer-director.md      ← エンジニアディレクター Instructions
    │   ├── frontend.md               ← フロントエンド Instructions
    │   ├── backend.md                ← バックエンド Instructions
    │   └── qa.md                     ← QA Instructions
    │
    ├── content/
    │   ├── content-director.md       ← コンテンツディレクター Instructions
    │   ├── brand-voice.md            ← ブランドボイス Instructions
    │   ├── root-cause.md             ← ルート構図 Instructions
    │   └── anti-ai-slop.md           ← アンチAIスロップ Instructions
    │
    └── business/
        ├── marketing-director.md     ← マーケティングディレクター Instructions
        ├── business-strategy.md      ← ビジネスストラテジー Instructions
        ├── partnership-manager.md    ← パートナーシップマネージャー Instructions
        └── legal-review.md           ← リーガルレビュー Instructions
```

---

## 実装スタート前の準備チェックリスト

### Microsoft 365 環境
- [ ] Microsoft 365 Business Standard 以上（Copilot Studio利用には別途ライセンス必要）
- [ ] Copilot Studio ライセンス（試用版でも可）
- [ ] Power Automate ライセンス（Premium コネクタ使用のためPremium推奨）
- [ ] Azure OpenAI Service（GPT-4o / GPT-4o-mini）リソース作成済み
- [ ] Azure Key Vault（APIキー管理）リソース作成済み

### SharePoint 設定
- [ ] SharePoint チームサイト「AI-Org-Intranet」作成
- [ ] `sharepoint-structure.md` に従ってフォルダ構成を作成
- [ ] `/Context/` 内の4ファイルを自分の情報で記入

### Teams 設定
- [ ] チーム「AI-Org」作成
- [ ] `teams-setup.md` に従ってチャンネル作成（Inbox / Morning Standup / Escalation / Agent Logs / Weekly Brief）

### Copilot Studio
- [ ] 各エージェントを `agents/` フォルダの Instructions を使って作成
- [ ] SharePoint コネクタを各エージェントに設定
- [ ] Power Automate アクションを各エージェントに紐付け
- [ ] Direct Line チャンネルを有効化（Power Automateからの呼び出し用）

### Power Automate
- [ ] `flows/power-automate-flows.md` に従って各フローを作成
- [ ] 環境変数を設定

---

## 推奨実装順序

1. **最初に**: SharePoint + Teams の基盤構築 + Contextファイルの記入
2. **Phase 1**: コンテンツチーム（4エージェント + PA-ContentReview フロー）
3. **Phase 2**: インフラチーム（2エージェント + PA-InboxCapture / PA-MorningStandup フロー）
4. **Phase 3**: エンジニアリングチーム（5エージェント + PA-NightlyQARun フロー）
5. **Phase 4**: ビジネスチーム（4エージェント + PA-WeeklyBrief フロー）

---

## 参考リソース

- [Microsoft Copilot Studio 公式ドキュメント](https://learn.microsoft.com/ja-jp/microsoft-copilot-studio/)
- [Power Automate 公式ドキュメント](https://learn.microsoft.com/ja-jp/power-automate/)
- [Azure OpenAI Service 公式ドキュメント](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/)
- [Copilot Studio Direct Line API](https://learn.microsoft.com/ja-jp/microsoft-copilot-studio/publication-connect-bot-to-custom-application)
