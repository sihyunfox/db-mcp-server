"""FastMCP 서버: MySQL 메타데이터 조회 도구."""
import argparse
import asyncio
import json
import threading
from typing import Any

from fastmcp import FastMCP

from . import config, metadata
from .db import DBConnectionError
from .metadata import MetadataError
from .rate_limiter import RateLimitExceeded, check_and_consume as rate_limit_check
from .validation import (
    ValidationError,
    validate_schema_name,
    validate_table_name,
    validate_table_names_list,
)
from . import audit

mcp = FastMCP("MySQL Metadata Server")

# 동시 실행 제한(선택). 0이면 미사용.
_concurrency_semaphore: threading.Semaphore | None = None
if config.MAX_CONCURRENT_REQUESTS > 0:
    _concurrency_semaphore = threading.Semaphore(config.MAX_CONCURRENT_REQUESTS)


def _acquire_concurrency() -> None:
    if _concurrency_semaphore:
        _concurrency_semaphore.acquire()


def _release_concurrency() -> None:
    if _concurrency_semaphore:
        _concurrency_semaphore.release()


def _to_json(value: Any) -> str:
    """Tool 반환값을 JSON 문자열로."""
    return json.dumps(value, ensure_ascii=False, indent=2)


@mcp.tool()
def list_tables(schema_name: str | None = None) -> str:
    """지정 스키마(또는 생략 시 전체)의 테이블 목록을 반환합니다."""
    try:
        validate_schema_name(schema_name)
        rate_limit_check()
        _acquire_concurrency()
        try:
            result = metadata.list_tables(schema_name=schema_name or None)
            audit.log("list_tables", "success", schema_name=schema_name)
            return _to_json(result)
        finally:
            _release_concurrency()
    except ValidationError as e:
        audit.log("list_tables", "rejected", schema_name=schema_name, reason="validation_failed")
        return _to_json({"error": str(e)})
    except RateLimitExceeded as e:
        audit.log("list_tables", "rejected", schema_name=schema_name, reason="rate_limit_exceeded")
        return _to_json({"error": e.message})
    except DBConnectionError as e:
        audit.log("list_tables", "rejected", schema_name=schema_name, reason="db_error")
        return _to_json({"error": str(e)})
    except Exception as e:
        audit.log("list_tables", "rejected", schema_name=schema_name, reason="error")
        return _to_json({"error": f"처리 중 오류: {e!s}"})


@mcp.tool()
def get_table_metadata(schema_name: str, table_name: str) -> str:
    """한 테이블에 대한 DDL 문서 작성에 필요한 전체 메타데이터를 반환합니다."""
    try:
        validate_schema_name(schema_name)
        validate_table_name(table_name)
        rate_limit_check()
        _acquire_concurrency()
        try:
            result = metadata.get_table_metadata(schema_name, table_name)
            audit.log("get_table_metadata", "success", schema_name=schema_name, table_name=table_name)
            return _to_json(result)
        finally:
            _release_concurrency()
    except ValidationError as e:
        audit.log("get_table_metadata", "rejected", schema_name=schema_name, table_name=table_name, reason="validation_failed")
        return _to_json({"error": str(e)})
    except RateLimitExceeded as e:
        audit.log("get_table_metadata", "rejected", schema_name=schema_name, table_name=table_name, reason="rate_limit_exceeded")
        return _to_json({"error": e.message})
    except MetadataError as e:
        audit.log("get_table_metadata", "rejected", schema_name=schema_name, table_name=table_name, reason="not_found")
        return _to_json({"error": str(e)})
    except DBConnectionError as e:
        audit.log("get_table_metadata", "rejected", schema_name=schema_name, table_name=table_name, reason="db_error")
        return _to_json({"error": str(e)})
    except Exception as e:
        audit.log("get_table_metadata", "rejected", schema_name=schema_name, table_name=table_name, reason="error")
        return _to_json({"error": f"처리 중 오류: {e!s}"})


@mcp.tool()
def get_tables_metadata(schema_name: str, table_names: list[str]) -> str:
    """여러 테이블에 대한 DDL 메타데이터를 한 번에 조회합니다. 존재하지 않는 테이블은 결과에 error로 표시됩니다."""
    try:
        validate_schema_name(schema_name)
        table_names = validate_table_names_list(table_names)
        rate_limit_check()
        _acquire_concurrency()
        try:
            result = metadata.get_tables_metadata(schema_name, table_names)
            audit.log("get_tables_metadata", "success", schema_name=schema_name, table_count=len(table_names))
            return _to_json(result)
        finally:
            _release_concurrency()
    except ValidationError as e:
        audit.log("get_tables_metadata", "rejected", schema_name=schema_name, reason="validation_failed")
        return _to_json({"error": str(e)})
    except RateLimitExceeded as e:
        audit.log("get_tables_metadata", "rejected", schema_name=schema_name, reason="rate_limit_exceeded")
        return _to_json({"error": e.message})
    except DBConnectionError as e:
        audit.log("get_tables_metadata", "rejected", schema_name=schema_name, reason="db_error")
        return _to_json({"error": str(e)})
    except Exception as e:
        audit.log("get_tables_metadata", "rejected", schema_name=schema_name, reason="error")
        return _to_json({"error": f"처리 중 오류: {e!s}"})


@mcp.tool()
def get_schema_overview(schema_name: str) -> str:
    """한 스키마의 테이블 목록과 외래키 관계 요약을 반환합니다 (DDL 문서 목차·개요용)."""
    try:
        validate_schema_name(schema_name)
        rate_limit_check()
        _acquire_concurrency()
        try:
            result = metadata.get_schema_overview(schema_name)
            audit.log("get_schema_overview", "success", schema_name=schema_name)
            return _to_json(result)
        finally:
            _release_concurrency()
    except ValidationError as e:
        audit.log("get_schema_overview", "rejected", schema_name=schema_name, reason="validation_failed")
        return _to_json({"error": str(e)})
    except RateLimitExceeded as e:
        audit.log("get_schema_overview", "rejected", schema_name=schema_name, reason="rate_limit_exceeded")
        return _to_json({"error": e.message})
    except DBConnectionError as e:
        audit.log("get_schema_overview", "rejected", schema_name=schema_name, reason="db_error")
        return _to_json({"error": str(e)})
    except Exception as e:
        audit.log("get_schema_overview", "rejected", schema_name=schema_name, reason="error")
        return _to_json({"error": f"처리 중 오류: {e!s}"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MySQL 메타데이터 MCP 서버")
    parser.add_argument(
        "--http",
        type=int,
        metavar="PORT",
        default=None,
        help="HTTP 모드로 실행 (예: --http 8000). 미지정 시 stdio 모드.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP 바인드 주소 (기본: 127.0.0.1)")
    args = parser.parse_args()

    if args.http is not None:
        asyncio.run(mcp.run_async(transport="http", host=args.host, port=args.http))
    else:
        mcp.run()
