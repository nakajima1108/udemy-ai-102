"""
Azure AI Search インデックスを作成し、ナレッジベース JSON をアップロードするスクリプト。
初回セットアップ時、またはインデックスを再構築する際に使用する。
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)
from openai import AzureOpenAI

load_dotenv()

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "tanium-troubleshoot-knowledge")
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge_base" / "tanium_troubleshoot_knowledge.json"


def build_index_definition() -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="symptom", type=SearchFieldDataType.String, analyzer_name="ja.microsoft"),
        SearchableField(name="cause", type=SearchFieldDataType.String, analyzer_name="ja.microsoft"),
        SearchableField(name="resolution", type=SearchFieldDataType.String, analyzer_name="ja.microsoft"),
        SearchableField(name="tanium_query", type=SearchFieldDataType.String),
        SimpleField(
            name="affected_os",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            facetable=True,
        ),
        SimpleField(name="severity", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(
            name="tags",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            facetable=True,
        ),
        SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SearchField(
            name="symptom_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="hnsw-profile",
        ),
        SearchField(
            name="resolution_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
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
                name="tanium-semantic",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="symptom"),
                    content_fields=[SemanticField(field_name="resolution")],
                    keywords_fields=[SemanticField(field_name="tags"), SemanticField(field_name="category")],
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


def create_or_update_index(index_client: SearchIndexClient) -> None:
    index_def = build_index_definition()
    index_client.create_or_update_index(index_def)
    print(f"インデックス '{INDEX_NAME}' を作成/更新しました。")


def generate_embedding(client: AzureOpenAI, text: str) -> list[float]:
    response = client.embeddings.create(model=EMBEDDING_DEPLOYMENT, input=text)
    return response.data[0].embedding


def prepare_documents(raw_docs: list[dict], openai_client: AzureOpenAI) -> list[dict]:
    documents = []
    for i, doc in enumerate(raw_docs):
        print(f"  ベクター生成中: {doc['id']} ({i + 1}/{len(raw_docs)})")
        doc["symptom_vector"] = generate_embedding(openai_client, doc["symptom"])
        doc["resolution_vector"] = generate_embedding(openai_client, doc["resolution"])
        documents.append(doc)
    return documents


def upload_documents(search_client: SearchClient, documents: list[dict]) -> None:
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        result = search_client.upload_documents(documents=batch)
        succeeded = sum(1 for r in result if r.succeeded)
        failed = len(result) - succeeded
        print(f"  アップロード完了: 成功={succeeded}, 失敗={failed} (バッチ {i // batch_size + 1})")


def main() -> None:
    if not KNOWLEDGE_BASE_PATH.exists():
        print(f"エラー: ナレッジベースファイルが見つかりません: {KNOWLEDGE_BASE_PATH}", file=sys.stderr)
        sys.exit(1)

    credential = AzureKeyCredential(SEARCH_API_KEY)
    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
    search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)
    openai_client = AzureOpenAI(
        azure_endpoint=OPENAI_ENDPOINT,
        api_key=OPENAI_API_KEY,
        api_version=OPENAI_API_VERSION,
    )

    print("Step 1: インデックスを作成/更新します...")
    create_or_update_index(index_client)

    print("Step 2: ナレッジベース JSON を読み込みます...")
    with open(KNOWLEDGE_BASE_PATH, encoding="utf-8") as f:
        knowledge_data = json.load(f)
    raw_docs = knowledge_data["documents"]
    print(f"  {len(raw_docs)} 件のドキュメントを読み込みました。")

    print("Step 3: ベクターを生成します...")
    documents = prepare_documents(raw_docs, openai_client)

    print("Step 4: Azure AI Search へアップロードします...")
    upload_documents(search_client, documents)

    print(f"\n完了: {len(documents)} 件のナレッジをインデックス '{INDEX_NAME}' にアップロードしました。")


if __name__ == "__main__":
    main()
