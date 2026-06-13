# Tanium トラブルシューティング AI エージェント

Microsoft Copilot Studio + Azure AI Search + Azure OpenAI を使用した端末・ネットワーク障害診断エージェント。

---

## アーキテクチャ概要

```
ユーザー (Teams / Web Chat)
        │
        ▼
┌─────────────────────────┐
│  Microsoft Copilot Studio│
│  ・トピック定義          │
│  ・生成AIノード          │
│  ・カスタムコネクタ      │
└────────────┬────────────┘
             │ HTTP (REST)
             ▼
┌─────────────────────────┐
│   Azure AI Search       │
│   ナレッジベースインデックス│
│   (ベクター + ハイブリッド検索) │
└────────────┬────────────┘
             │ Embedding / Completion
             ▼
┌─────────────────────────┐
│   Azure OpenAI Service  │
│   ・text-embedding-3-small │
│   ・gpt-4o              │
└─────────────────────────┘
             │ Tanium クエリ実行
             ▼
┌─────────────────────────┐
│   Tanium API / Connect  │
│   エンドポイント管理     │
└─────────────────────────┘
```

### コンポーネント説明

| コンポーネント | 役割 |
|---|---|
| Microsoft Copilot Studio | 会話フロー管理・ユーザーインターフェース |
| Azure AI Search | ナレッジベースのインデックスと検索（ベクター + キーワードのハイブリッド） |
| Azure OpenAI (gpt-4o) | 検索結果を基にした回答生成 |
| Azure OpenAI (embedding) | ナレッジのベクター化 |
| Tanium API | エンドポイントへのクエリ実行・実データ取得 |

---

## ディレクトリ構成

```
9_TaniumTroubleshootAgent/
├── README.md
├── knowledge_base/
│   └── tanium_troubleshoot_knowledge.json   # トラブルシューティングナレッジ
├── scripts/
│   ├── upload_knowledge.py                  # ナレッジを Azure AI Search へアップロード
│   └── update_knowledge.py                  # 新規ケースをナレッジに追加
└── copilot_studio/
    ├── topic_definitions.json               # トピック定義（設計仕様）
    └── system_prompt.txt                    # 生成AIノード用システムプロンプト
```

---

## 前提条件

- Azure サブスクリプション
- Azure AI Search リソース（Standard S1 以上推奨）
- Azure OpenAI リソース（gpt-4o + text-embedding-3-small をデプロイ済み）
- Microsoft Copilot Studio ライセンス（Power Platform）
- Tanium Server（API アクセス可能）
- Python 3.11 以上

---

## セットアップ手順

### 1. Azure リソースの準備

#### Azure AI Search

```bash
az search service create \
  --name <your-search-service-name> \
  --resource-group <your-rg> \
  --sku Standard \
  --location japaneast
```

#### Azure OpenAI

Azure Portal で以下のモデルをデプロイする：
- `text-embedding-3-small`（デプロイ名: `text-embedding-3-small`）
- `gpt-4o`（デプロイ名: `gpt-4o`）

### 2. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成する：

```dotenv
# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<your-service>.search.windows.net
AZURE_SEARCH_API_KEY=<your-admin-key>
AZURE_SEARCH_INDEX_NAME=tanium-troubleshoot-knowledge

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o

# Tanium
TANIUM_SERVER_URL=https://<your-tanium-server>
TANIUM_API_KEY=<your-tanium-api-key>
```

### 3. Python 依存パッケージのインストール

```bash
pip install azure-search-documents azure-identity openai python-dotenv
```

### 4. ナレッジベースのアップロード

Azure AI Search インデックスを作成し、サンプルデータをアップロードする：

```bash
cd scripts
python upload_knowledge.py
```

成功すると以下が実行される：
1. `tanium-troubleshoot-knowledge` インデックスの作成（存在しない場合）
2. `knowledge_base/tanium_troubleshoot_knowledge.json` からドキュメントをアップロード
3. 各ドキュメントのベクターフィールド生成

### 5. 新規ナレッジの追加

新しいトラブルシューティングケースを追加する：

```bash
python update_knowledge.py \
  --symptom "端末でアプリケーションが起動しない" \
  --cause "DLL ファイルの破損" \
  --resolution "SFC /scannow を実行し、破損ファイルを修復する" \
  --tanium_query "Get File Exists[C:\\Windows\\System32\\vcruntime140.dll] from all machines" \
  --affected_os "Windows 10,Windows 11" \
  --severity "high" \
  --category "アプリケーション障害"
```

または JSON ファイルからバッチ追加：

```bash
python update_knowledge.py --file new_cases.json
```

### 6. Copilot Studio の設定

#### カスタムコネクタの作成

1. Power Platform 管理センター → **カスタムコネクタ** → **新規作成**
2. Swagger 定義に Azure AI Search REST API を設定：
   - ベース URL: `https://<your-service>.search.windows.net`
   - 認証: API キー（ヘッダー `api-key`）
3. 以下のアクションを定義：
   - `SearchDocuments`: `POST /indexes/tanium-troubleshoot-knowledge/docs/search?api-version=2024-05-01-preview`

#### トピックのインポート

`copilot_studio/topic_definitions.json` を参照し、以下のトピックを手動で作成する：

| トピック名 | トリガーフレーズ例 |
|---|---|
| 端末トラブル診断 | "PCが起動しない", "端末が重い", "ブルースクリーンが出る" |
| ネットワーク診断 | "ネットに繋がらない", "VPNが切れる", "遅い" |
| Taniumクエリ実行 | "Taniumでクエリを実行して", "センサーデータを取得" |
| ナレッジ更新 | "新しい解決策を登録", "ナレッジを追加" |

#### 生成AIノードの設定

各トピックの回答生成ステップで：
1. **生成AIを使用** ノードを追加
2. `copilot_studio/system_prompt.txt` の内容をシステムプロンプトに設定
3. データソースに Azure AI Search カスタムコネクタを接続

---

## ナレッジベースのスキーマ

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | string | ドキュメント一意ID（UUID） |
| `symptom` | string | 症状・障害内容 |
| `cause` | string | 原因 |
| `resolution` | string | 解決手順 |
| `tanium_query` | string | Tanium センサークエリ |
| `affected_os` | string[] | 対象OS |
| `severity` | string | 重要度（low / medium / high / critical） |
| `category` | string | カテゴリ（ネットワーク / 端末 / Tanium クライアント等） |
| `tags` | string[] | 検索用タグ |
| `created_at` | string | 作成日時（ISO 8601） |
| `updated_at` | string | 更新日時（ISO 8601） |
| `symptom_vector` | float[] | symptom のベクター表現（1536次元） |
| `resolution_vector` | float[] | resolution のベクター表現（1536次元） |

---

## ナレッジの継続的な更新フロー

```
新規インシデント発生
        │
        ▼
エンジニアが解決策を確認・文書化
        │
        ▼
update_knowledge.py で Azure AI Search へ追加
        │
        ▼
Copilot Studio エージェントが次回から参照可能
        │
        ▼
（オプション）月次レビューで古いナレッジを更新・廃止
```

---

## セキュリティ考慮事項

- `.env` ファイルを Git にコミットしない（`.gitignore` に追加済みであることを確認）
- Azure AI Search の API キーは Azure Key Vault で管理することを推奨
- Tanium API キーは最小権限の原則に従い、Read-Only 権限で設定
- Copilot Studio のカスタムコネクタ認証情報は Power Platform 環境変数で管理

---

## トラブルシューティング（本システム自体の障害対応）

| 問題 | 確認事項 |
|---|---|
| 検索結果が返らない | Azure AI Search インデックスのドキュメント数を確認（Azure Portal） |
| ベクター検索が機能しない | embedding デプロイ名が `.env` と一致しているか確認 |
| Copilot Studio がコネクタエラーを返す | カスタムコネクタのテストタブで接続テストを実行 |
| Tanium クエリが失敗する | Tanium API キーの有効期限と権限を確認 |
