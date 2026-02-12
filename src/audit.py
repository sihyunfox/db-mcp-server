"""감사 로그: 도구 호출·성공/거부·사유 기록. 비밀/토큰 미포함."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_record(
    tool: str,
    status: str,
    *,
    schema_name: str | None = None,
    table_name: str | None = None,
    table_count: int | None = None,
    reason: str | None = None,
    client_id: str | None = None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "ts": _timestamp_utc(),
        "tool": tool,
        "status": status,
    }
    if schema_name is not None:
        rec["schema"] = schema_name
    if table_name is not None:
        rec["table"] = table_name
    if table_count is not None:
        rec["table_count"] = table_count
    if reason is not None:
        rec["reason"] = reason
    if client_id is not None:
        rec["client_id"] = client_id
    return rec


def _write_line(line: str) -> None:
    if config.AUDIT_LOG_PATH:
        path = Path(config.AUDIT_LOG_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    else:
        print(line, file=sys.stderr, flush=True)


def log(
    tool: str,
    status: str,
    *,
    schema_name: str | None = None,
    table_name: str | None = None,
    table_count: int | None = None,
    reason: str | None = None,
    client_id: str | None = None,
) -> None:
    """감사 로그 1건 기록. AUDIT_ENABLED가 False면 무시."""
    if not config.AUDIT_ENABLED:
        return
    rec = _build_record(
        tool=tool,
        status=status,
        schema_name=schema_name,
        table_name=table_name,
        table_count=table_count,
        reason=reason,
        client_id=client_id,
    )
    if config.AUDIT_FORMAT == "json":
        line = json.dumps(rec, ensure_ascii=False)
    else:
        line = json.dumps(rec, ensure_ascii=False)
    _write_line(line)
