"""
Tanium トラブルシューティングナレッジに新規ケースを追加するスクリプト。
追加後は upload_knowledge.py を実行してインデックスに反映する。

使用方法:
  python update_knowledge.py \\
    --symptom "症状の説明" \\
    --cause "原因の説明" \\
    --resolution "解決手順" \\
    --tanium_query "Get ... from all machines" \\
    --affected_os "Windows,Linux" \\
    --severity "high" \\
    --category "tanium_client"
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

KNOWLEDGE_FILE = Path(__file__).parent.parent / "knowledge_base" / "tanium_troubleshoot_knowledge.json"

VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_CATEGORIES = {"tanium_client", "network", "performance", "patch", "security", "other"}


def generate_id(cases: list[dict]) -> str:
    numbers = []
    for case in cases:
        m = re.match(r"TAN-(\d+)", case.get("id", ""))
        if m:
            numbers.append(int(m.group(1)))
    next_num = max(numbers, default=0) + 1
    return f"TAN-{next_num:03d}"


def validate_args(args: argparse.Namespace) -> None:
    if args.severity not in VALID_SEVERITIES:
        raise ValueError(f"severity は {VALID_SEVERITIES} のいずれかを指定してください")
    if args.category not in VALID_CATEGORIES:
        raise ValueError(f"category は {VALID_CATEGORIES} のいずれかを指定してください")
    if not args.symptom.strip():
        raise ValueError("symptom は必須です")
    if not args.resolution.strip():
        raise ValueError("resolution は必須です")


def add_case(args: argparse.Namespace) -> str:
    validate_args(args)

    knowledge = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    cases = knowledge["cases"]

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    new_id = generate_id(cases)

    new_case = {
        "id": new_id,
        "category": args.category,
        "severity": args.severity,
        "symptom": args.symptom.strip(),
        "cause": args.cause.strip() if args.cause else "",
        "resolution": args.resolution.strip(),
        "tanium_query": args.tanium_query.strip() if args.tanium_query else "",
        "affected_os": [os.strip() for os in args.affected_os.split(",")] if args.affected_os else [],
        "tags": [t.strip() for t in args.tags.split(",")] if args.tags else [],
        "created_at": now,
        "updated_at": now,
    }

    cases.append(new_case)
    knowledge["cases"] = cases
    knowledge["last_updated"] = now[:10]

    KNOWLEDGE_FILE.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"ケース {new_id} を追加しました。")
    print(f"インデックスへの反映: python scripts/upload_knowledge.py")
    return new_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Taniumナレッジに新規ケースを追加する")
    parser.add_argument("--symptom", required=True, help="障害症状の説明")
    parser.add_argument("--cause", default="", help="原因の説明")
    parser.add_argument("--resolution", required=True, help="解決手順")
    parser.add_argument("--tanium_query", default="", help="診断に使うTaniumクエリ")
    parser.add_argument("--affected_os", default="", help="影響OS (カンマ区切り: Windows,Linux,macOS)")
    parser.add_argument("--severity", required=True, choices=list(VALID_SEVERITIES), help="重大度")
    parser.add_argument("--category", required=True, choices=list(VALID_CATEGORIES), help="カテゴリ")
    parser.add_argument("--tags", default="", help="タグ (カンマ区切り)")
    add_case(parser.parse_args())
