"""
Azure AI Search へ Tanium トラブルシューティングナレッジをアップロードするスクリプト。
初回セットアップ時および全件再インデックス時に使用する。

使用方法:
  python upload_knowledge.py                  # 増分アップロード (デフォルト)
  python upload_knowledge.py --full-reindex   # インデックス削除→再作成→全件アップロード
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_KEY"]
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "tanium-knowledge")
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
OPENAI_KEY = os.environ["AZURE_OPENAI_API_KEY"]
EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")

KNOWLEDGE_FILE = Path(__file__).parent.parent / "knowledge_base" / "tanium_troubleshoot_knowledge.json"


def get_index_schema() -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(name="severity", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(name="symptom", type=SearchFieldDataType.String, searchable=True, analyzer_name="ja.microsoft"),
        SearchField(name="cause", type=SearchFieldDataType.String, searchable=True, analyzer_name="ja.microsoft"),
        SearchField(name="resolution", type=SearchFieldDataType.String, searchable=True, analyzer_name="ja.microsoft"),
        SearchField(name="tanium_query", type=SearchFieldDataType.String, searchable=True),
        SearchField(
            name="affected_os",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True,
        ),
        SearchField(
            name="tags",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True,
        ),
        SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, sortable=True),
        SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, sortable=True),
        SearchField(
            name="symptom_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="hnsw-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="default",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="symptom"),
                    content_fields=[
                        SemanticField(field_name="cause"),
                        SemanticField(field_name="resolution"),
                    ],
                    keywords_fields=[SemanticField(field_name="tags")],
                ),
            )
        ]
    )

    return SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def embed_text(client: AzureOpenAI, text: str) -> list[float]:
    response = client.embeddings.create(input=text, model=EMBEDDING_DEPLOYMENT)
    return response.data[0].embedding


def prepare_document(case: dict, embedding_client: AzureOpenAI) -> dict:
    symptom_vector = embed_text(embedding_client, case["symptom"])
    return {
        "id": case["id"],
        "category": case["category"],
        "severity": case["severity"],
        "symptom": case["symptom"],
        "cause": case["cause"],
        "resolution": case["resolution"],
        "tanium_query": case.get("tanium_query", ""),
        "affected_os": case.get("affected_os", []),
        "tags": case.get("tags", []),
        "created_at": case.get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": case.get("updated_at", datetime.now(timezone.utc).isoformat()),
        "symptom_vector": symptom_vector,
    }


def create_or_recreate_index(index_client: SearchIndexClient, full_reindex: bool) -> None:
    existing = [idx.name for idx in index_client.list_indexes()]
    if INDEX_NAME in existing:
        if full_reindex:
            print(f"既存インデックス '{INDEX_NAME}' を削除します...")
            index_client.delete_index(INDEX_NAME)
        else:
            return
    print(f"インデックス '{INDEX_NAME}' を作成します...")
    index_client.create_index(get_index_schema())


def upload(full_reindex: bool = False) -> None:
    credential = AzureKeyCredential(SEARCH_KEY)
    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
    search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)
    embedding_client = AzureOpenAI(azure_endpoint=OPENAI_ENDPOINT, api_key=OPENAI_KEY, api_version="2024-02-01")

    create_or_recreate_index(index_client, full_reindex)

    knowledge = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    cases = knowledge["cases"]

    documents = []
    for i, case in enumerate(cases):
        print(f"  埋め込みベクター生成中 [{i + 1}/{len(cases)}]: {case['id']}")
        documents.append(prepare_document(case, embedding_client))

    result = search_client.upload_documents(documents=documents)
    succeeded = sum(1 for r in result if r.succeeded)
    print(f"\nアップロード完了: {succeeded}/{len(documents)} 件成功")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Taniumナレッジを Azure AI Search にアップロードする")
    parser.add_argument("--full-reindex", action="store_true", help="インデックスを削除して全件再作成する")
    args = parser.parse_args()
    upload(full_reindex=args.full_reindex)
