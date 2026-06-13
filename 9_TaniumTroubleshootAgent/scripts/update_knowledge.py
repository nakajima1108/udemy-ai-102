"""
新しいトラブルシューティングケースをナレッジベースに追加するスクリプト。
コマンドライン引数による単件追加、または JSON ファイルによるバッチ追加に対応。

使用例:
  # 単件追加
  python update_knowledge.py --symptom "..." --cause "..." --resolution "..." \
    --tanium_query "..." --affected_os "Windows 10,Windows 11" \
    --severity "medium" --category "ネットワーク" --tags "tag1,tag2"

  # バッチ追加 (JSON ファイル)
  python update_knowledge.py --file new_cases.json
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

load_dotenv()

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "tanium-troubleshoot-knowledge")
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge_base" / "tanium_troubleshoot_knowledge.json"

VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def generate_embedding(client: AzureOpenAI, text: str) -> list[float]:
    response = client.embeddings.create(model=EMBEDDING_DEPLOYMENT, input=text)
    return response.data[0].embedding


def build_document(case: dict, openai_client: AzureOpenAI) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    doc_id = case.get("id") or f"kb-{uuid.uuid4().hex[:8]}"

    affected_os = case.get("affected_os", [])
    if isinstance(affected_os, str):
        affected_os = [os_name.strip() for os_name in affected_os.split(",") if os_name.strip()]

    tags = case.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    severity = case.get("severity", "medium").lower()
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"severity は {VALID_SEVERITIES} のいずれかである必要があります。指定値: '{severity}'")

    doc = {
        "id": doc_id,
        "category": case["category"],
        "symptom": case["symptom"],
        "cause": case["cause"],
        "resolution": case["resolution"],
        "tanium_query": case.get("tanium_query", ""),
        "affected_os": affected_os,
        "severity": severity,
        "tags": tags,
        "created_at": case.get("created_at", now),
        "updated_at": now,
    }

    print(f"  ベクター生成中: {doc_id}")
    doc["symptom_vector"] = generate_embedding(openai_client, doc["symptom"])
    doc["resolution_vector"] = generate_embedding(openai_client, doc["resolution"])

    return doc


def sync_to_local_knowledge_base(docs: list[dict]) -> None:
    """追加したドキュメントをローカルの JSON ファイルにも反映する（ベクターフィールドは除外）。"""
    if not KNOWLEDGE_BASE_PATH.exists():
        print("  警告: ローカルナレッジベースファイルが見つかりません。ローカル同期をスキップします。")
        return

    with open(KNOWLEDGE_BASE_PATH, encoding="utf-8") as f:
        knowledge_data = json.load(f)

    existing_ids = {d["id"] for d in knowledge_data["documents"]}

    strip_fields = {"symptom_vector", "resolution_vector"}
    added_count = 0
    updated_count = 0

    for doc in docs:
        clean_doc = {k: v for k, v in doc.items() if k not in strip_fields}
        if clean_doc["id"] in existing_ids:
            knowledge_data["documents"] = [
                clean_doc if d["id"] == clean_doc["id"] else d
                for d in knowledge_data["documents"]
            ]
            updated_count += 1
        else:
            knowledge_data["documents"].append(clean_doc)
            added_count += 1

    with open(KNOWLEDGE_BASE_PATH, "w", encoding="utf-8") as f:
        json.dump(knowledge_data, f, ensure_ascii=False, indent=2)

    print(f"  ローカルファイル同期完了: 追加={added_count}, 更新={updated_count}")


def upload_to_search(search_client: SearchClient, docs: list[dict]) -> None:
    result = search_client.merge_or_upload_documents(documents=docs)
    succeeded = sum(1 for r in result if r.succeeded)
    failed = len(result) - succeeded
    if failed > 0:
        failed_ids = [r.key for r in result if not r.succeeded]
        raise RuntimeError(f"アップロード失敗: {failed} 件。失敗ID: {failed_ids}")
    print(f"  Azure AI Search アップロード完了: {succeeded} 件")


def parse_single_case_from_args(args: argparse.Namespace) -> dict:
    required = ["symptom", "cause", "resolution", "category"]
    missing = [f for f in required if not getattr(args, f, None)]
    if missing:
        raise ValueError(f"必須フィールドが不足しています: {', '.join(missing)}")

    return {
        "symptom": args.symptom,
        "cause": args.cause,
        "resolution": args.resolution,
        "category": args.category,
        "tanium_query": args.tanium_query or "",
        "affected_os": args.affected_os or "",
        "severity": args.severity or "medium",
        "tags": args.tags or "",
    }


def load_cases_from_file(file_path: str) -> list[dict]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "documents" in data:
        return data["documents"]
    raise ValueError("JSONフォーマットが不正です。リスト形式、または {'documents': [...]} 形式である必要があります。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tanium ナレッジベースに新規ケースを追加します。")
    parser.add_argument("--file", help="追加するケースの JSON ファイルパス（バッチ追加）")
    parser.add_argument("--symptom", help="症状の説明")
    parser.add_argument("--cause", help="原因の説明")
    parser.add_argument("--resolution", help="解決手順")
    parser.add_argument("--category", help="カテゴリ（例: ネットワーク, 端末パフォーマンス）")
    parser.add_argument("--tanium_query", help="Tanium センサークエリ")
    parser.add_argument("--affected_os", help="対象OS（カンマ区切り）")
    parser.add_argument("--severity", choices=list(VALID_SEVERITIES), default="medium", help="重要度")
    parser.add_argument("--tags", help="タグ（カンマ区切り）")
    args = parser.parse_args()

    if not args.file and not args.symptom:
        parser.print_help()
        sys.exit(1)

    credential = AzureKeyCredential(SEARCH_API_KEY)
    search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)
    openai_client = AzureOpenAI(
        azure_endpoint=OPENAI_ENDPOINT,
        api_key=OPENAI_API_KEY,
        api_version=OPENAI_API_VERSION,
    )

    if args.file:
        print(f"ファイルからケースを読み込みます: {args.file}")
        raw_cases = load_cases_from_file(args.file)
    else:
        raw_cases = [parse_single_case_from_args(args)]

    print(f"{len(raw_cases)} 件のケースを処理します。")

    docs = []
    for i, case in enumerate(raw_cases):
        print(f"\nケース {i + 1}/{len(raw_cases)} を処理中...")
        doc = build_document(case, openai_client)
        docs.append(doc)

    print("\nAzure AI Search へアップロードします...")
    upload_to_search(search_client, docs)

    print("ローカルナレッジベースファイルを同期します...")
    sync_to_local_knowledge_base(docs)

    print(f"\n完了: {len(docs)} 件のナレッジを追加/更新しました。")


if __name__ == "__main__":
    main()
