"""MySQL 읽기 전용 연결. SELECT만 사용."""
import contextlib
from typing import Generator

import pymysql
from pymysql.cursors import DictCursor

from . import config


class DBConnectionError(Exception):
    """DB 연결/쿼리 실패 시 사용."""
    pass


@contextlib.contextmanager
def get_connection() -> Generator[pymysql.connections.Connection, None, None]:
    """MySQL 연결 컨텍스트 매니저. 읽기 전용 사용만 가정."""
    conn = None
    try:
        conn = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME if config.DB_NAME else None,
            charset="utf8mb4",
            connect_timeout=config.DB_CONNECT_TIMEOUT,
            read_timeout=config.DB_QUERY_TIMEOUT,
            write_timeout=config.DB_QUERY_TIMEOUT,
            ssl=config.DB_SSL,
            cursorclass=DictCursor,
        )
        yield conn
    except pymysql.Error as e:
        msg = str(e)
        if "timeout" in msg.lower() or "timed out" in msg.lower():
            raise DBConnectionError(f"DB 연결 또는 쿼리 타임아웃: {msg}") from e
        raise DBConnectionError(f"DB 연결 실패: {msg}") from e
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
