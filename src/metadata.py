"""Information Schema 기반 메타데이터 조회. SELECT만 사용."""
from typing import Any

from . import config
from .db import get_connection

# 시스템 스키마 제외용 (전체 목록 시)
_SYSTEM_SCHEMAS = ("information_schema", "mysql", "performance_schema", "sys")


class MetadataError(Exception):
    """스키마/테이블 없음 등 메타데이터 조회 오류."""
    pass


def list_tables(schema_name: str | None = None) -> list[dict[str, Any]]:
    """지정 스키마(또는 전체)의 테이블 목록 반환."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            if schema_name:
                cur.execute(
                    """
                    SELECT TABLE_SCHEMA AS `schema`, TABLE_NAME AS table_name, TABLE_COMMENT AS table_comment
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_SCHEMA, TABLE_NAME
                    """,
                    (schema_name,),
                )
            else:
                cur.execute(
                    """
                    SELECT TABLE_SCHEMA AS `schema`, TABLE_NAME AS table_name, TABLE_COMMENT AS table_comment
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA NOT IN (%s, %s, %s, %s) AND TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_SCHEMA, TABLE_NAME
                    """,
                    _SYSTEM_SCHEMAS,
                )
            rows = cur.fetchall()
    result = [dict(row) for row in rows]
    if config.MAX_LIST_TABLES_RESULT > 0 and len(result) > config.MAX_LIST_TABLES_RESULT:
        result = result[: config.MAX_LIST_TABLES_RESULT]
    return result


def get_table_metadata(schema_name: str, table_name: str) -> dict[str, Any]:
    """한 테이블에 대한 DDL 문서용 전체 메타데이터 반환."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 테이블 존재 여부 및 테이블 정의
            cur.execute(
                """
                SELECT TABLE_NAME AS table_name, ENGINE AS engine, TABLE_COLLATION AS table_collation,
                       TABLE_COMMENT AS table_comment, ROW_FORMAT AS row_format
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND TABLE_TYPE = 'BASE TABLE'
                """,
                (schema_name, table_name),
            )
            table_row = cur.fetchone()
            if not table_row:
                raise MetadataError(f"스키마 또는 테이블이 존재하지 않습니다: {schema_name}.{table_name}")

            table_info = dict(table_row)

            # 2. 컬럼
            cur.execute(
                """
                SELECT COLUMN_NAME AS column_name, COLUMN_TYPE AS data_type, IS_NULLABLE AS nullable,
                       COLUMN_DEFAULT AS default_value, EXTRA AS extra, COLUMN_COMMENT AS column_comment
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                (schema_name, table_name),
            )
            columns = [dict(r) for r in cur.fetchall()]

            # 3. PRIMARY KEY / UNIQUE (KEY_COLUMN_USAGE + TABLE_CONSTRAINTS)
            cur.execute(
                """
                SELECT kcu.CONSTRAINT_NAME, tc.CONSTRAINT_TYPE, kcu.COLUMN_NAME, kcu.ORDINAL_POSITION
                FROM information_schema.KEY_COLUMN_USAGE kcu
                JOIN information_schema.TABLE_CONSTRAINTS tc
                  ON kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA AND kcu.TABLE_NAME = tc.TABLE_NAME
                     AND kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
                WHERE kcu.TABLE_SCHEMA = %s AND kcu.TABLE_NAME = %s
                  AND tc.CONSTRAINT_TYPE IN ('PRIMARY KEY', 'UNIQUE')
                ORDER BY tc.CONSTRAINT_TYPE, kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
                """,
                (schema_name, table_name),
            )
            pk_cols: list[str] = []
            unique_keys: list[dict[str, Any]] = []  # [{ constraint_name, columns: [] }]
            current_unique: dict[str, Any] | None = None
            for r in cur.fetchall():
                r = dict(r)
                if r["CONSTRAINT_TYPE"] == "PRIMARY KEY":
                    pk_cols.append(r["COLUMN_NAME"])
                else:
                    if current_unique is None or current_unique["constraint_name"] != r["CONSTRAINT_NAME"]:
                        current_unique = {"constraint_name": r["CONSTRAINT_NAME"], "columns": []}
                        unique_keys.append(current_unique)
                    current_unique["columns"].append(r["COLUMN_NAME"])

            # 4. 인덱스 (STATISTICS, PK/UNIQUE 제외한 일반 인덱스)
            cur.execute(
                """
                SELECT INDEX_NAME AS index_name, COLUMN_NAME AS column_name, SEQ_IN_INDEX AS seq,
                       NON_UNIQUE AS non_unique
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
                """,
                (schema_name, table_name),
            )
            index_groups: dict[str, list[str]] = {}
            for r in cur.fetchall():
                r = dict(r)
                name = r["index_name"]
                if name not in index_groups:
                    index_groups[name] = []
                index_groups[name].append(r["column_name"])
            indexes = [
                {"index_name": name, "columns": cols, "non_unique": True}
                for name, cols in index_groups.items()
                if name != "PRIMARY" and not any(u["constraint_name"] == name for u in unique_keys)
            ]

            # 5. 외래키
            cur.execute(
                """
                SELECT kcu.CONSTRAINT_NAME AS fk_name, kcu.COLUMN_NAME AS column_name,
                       kcu.REFERENCED_TABLE_SCHEMA AS ref_schema, kcu.REFERENCED_TABLE_NAME AS ref_table,
                       kcu.REFERENCED_COLUMN_NAME AS ref_column,
                       rc.UPDATE_RULE AS update_rule, rc.DELETE_RULE AS delete_rule
                FROM information_schema.KEY_COLUMN_USAGE kcu
                JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                  ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                     AND kcu.TABLE_SCHEMA = rc.CONSTRAINT_SCHEMA
                WHERE kcu.TABLE_SCHEMA = %s AND kcu.TABLE_NAME = %s AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
                """,
                (schema_name, table_name),
            )
            fk_rows = cur.fetchall()
            foreign_keys: list[dict[str, Any]] = []
            fk_by_name: dict[str, dict[str, Any]] = {}
            for r in fk_rows:
                r = dict(r)
                name = r["fk_name"]
                if name not in fk_by_name:
                    fk_by_name[name] = {
                        "constraint_name": name,
                        "columns": [],
                        "referenced_schema": r["ref_schema"],
                        "referenced_table": r["ref_table"],
                        "referenced_columns": [],
                        "update_rule": r["update_rule"],
                        "delete_rule": r["delete_rule"],
                    }
                    foreign_keys.append(fk_by_name[name])
                fk_by_name[name]["columns"].append(r["column_name"])
                fk_by_name[name]["referenced_columns"].append(r["ref_column"])

            # 6. CHECK 제약 (MySQL 8.0.16+)
            check_constraints: list[dict[str, Any]] = []
            try:
                cur.execute(
                    """
                    SELECT CONSTRAINT_NAME AS constraint_name, CHECK_CLAUSE AS check_clause
                    FROM information_schema.CHECK_CONSTRAINTS
                    WHERE CONSTRAINT_SCHEMA = %s AND CONSTRAINT_NAME IN (
                        SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_TYPE = 'CHECK'
                    )
                    """,
                    (schema_name, schema_name, table_name),
                )
                check_constraints = [dict(r) for r in cur.fetchall()]
            except Exception:
                pass  # 구버전 MySQL이면 CHECK_CONSTRAINTS 없을 수 있음

            return {
                "table": table_info,
                "columns": columns,
                "primary_key": pk_cols,
                "unique_keys": unique_keys,
                "indexes": indexes,
                "foreign_keys": foreign_keys,
                "check_constraints": check_constraints,
            }


def get_tables_metadata(schema_name: str, table_names: list[str]) -> list[dict[str, Any]]:
    """여러 테이블에 대한 DDL 메타데이터를 한 번에 조회. 실패한 테이블은 error 필드로 표시."""
    result: list[dict[str, Any]] = []
    for table_name in table_names:
        try:
            result.append(get_table_metadata(schema_name, table_name))
        except MetadataError as e:
            result.append({"error": str(e), "schema": schema_name, "table_name": table_name})
        except Exception as e:
            result.append({"error": str(e), "schema": schema_name, "table_name": table_name})
    return result


def get_schema_overview(schema_name: str) -> dict[str, Any]:
    """한 스키마의 테이블 목록과 FK 관계 요약 반환 (DDL 문서 목차·개요용)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT TABLE_NAME AS table_name, TABLE_COMMENT AS table_comment
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
                """,
                (schema_name,),
            )
            tables = [dict(r) for r in cur.fetchall()]

            cur.execute(
                """
                SELECT kcu.TABLE_NAME AS from_table, kcu.COLUMN_NAME AS from_column,
                       kcu.REFERENCED_TABLE_NAME AS to_table, kcu.REFERENCED_COLUMN_NAME AS to_column,
                       kcu.CONSTRAINT_NAME AS fk_name
                FROM information_schema.KEY_COLUMN_USAGE kcu
                WHERE kcu.TABLE_SCHEMA = %s AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME
                """,
                (schema_name,),
            )
            rows = cur.fetchall()
            relationships: list[dict[str, Any]] = []
            seen: set[tuple[str, str, str, str]] = set()
            for r in rows:
                r = dict(r)
                key = (r["from_table"], r["from_column"], r["to_table"], r["to_column"])
                if key in seen:
                    continue
                seen.add(key)
                relationships.append({
                    "from_table": r["from_table"],
                    "from_column": r["from_column"],
                    "to_table": r["to_table"],
                    "to_column": r["to_column"],
                    "fk_name": r["fk_name"],
                })

            return {"schema": schema_name, "tables": tables, "relationships": relationships}
