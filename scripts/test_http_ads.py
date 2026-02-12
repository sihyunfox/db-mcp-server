"""
HTTP로 구동 중인 db-mcp-server에 연결해 ads 테이블(또는 지정 테이블) 메타데이터를 조회하는 스크립트.

사용 전에 서버를 HTTP 모드로 실행하세요:
  python -m src.server --http 8000

실행 예:
  python scripts/test_http_ads.py
  python scripts/test_http_ads.py --port 8000 --schema mydb
  python scripts/test_http_ads.py --port 8000 --schema mydb --table my_table
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from fastmcp import Client
    import httpx
except ImportError:
    print("fastmcp가 필요합니다: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


def parse_args():
    p = argparse.ArgumentParser(description="HTTP MCP 서버에서 테이블 메타데이터 조회 (기본: ads)")
    p.add_argument("--url", default=None, help="서버 URL (예: http://localhost:8000/mcp). 지정 시 --port 무시")
    p.add_argument("--port", type=int, default=None, help="서버 포트 (기본: 8000)")
    p.add_argument("--schema", default=None, help="스키마명 (미지정 시 환경변수 DB_NAME 사용)")
    p.add_argument("--table", default="ads", help="테이블명 (기본: ads)")
    return p.parse_args()


async def main():
    args = parse_args()

    if args.url:
        base_url = args.url.rstrip("/")
    else:
        port = args.port
        if port is None:
            port = int(os.getenv("MCP_HTTP_PORT", "8000"))
        base_url = f"http://127.0.0.1:{port}/mcp"

    schema = args.schema or os.getenv("DB_NAME", "")
    if not schema:
        print("스키마를 지정하세요: --schema mydb 또는 환경변수 DB_NAME", file=sys.stderr)
        sys.exit(1)

    print(f"연결: {base_url}", file=sys.stderr)
    print(f"조회: {schema}.{args.table}", file=sys.stderr)

    try:
        async with Client(base_url) as client:
            result = await client.call_tool(
                "get_table_metadata",
                {"schema_name": schema, "table_name": args.table},
            )
    except httpx.ConnectError as e:
        print(
            f"연결 실패: {base_url}\n"
            "MCP 서버가 해당 주소에서 실행 중인지 확인하세요.\n"
            "예: python -m src.server --http <PORT>",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)

    # FastMCP CallToolResult: content 리스트의 첫 번째 블록이 텍스트
    if hasattr(result, "content") and result.content:
        block = result.content[0]
        text = block.text if hasattr(block, "text") else str(block)
    else:
        text = str(result)

    try:
        data = json.loads(text)
        if "error" in data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
            sys.exit(1)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(text)


if __name__ == "__main__":
    asyncio.run(main())
