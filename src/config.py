"""환경 변수 로드 및 설정."""
import os
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 루트 기준 .env 로드 (src에서 실행해도 상위 디렉터리 .env 사용)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key, "").strip().lower()
    if raw in ("", "0", "false", "no"):
        return False
    if raw in ("1", "true", "yes"):
        return True
    return default


# DB 설정
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = _int("DB_PORT", 3306)
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_SSL = _bool("DB_SSL", False)
DB_CONNECT_TIMEOUT = _int("DB_CONNECT_TIMEOUT", 10)
DB_QUERY_TIMEOUT = _int("DB_QUERY_TIMEOUT", 30)

# 처리량 제한: 분당 최대 Tool 호출 횟수. 0 또는 음수면 제한 없음. 미설정 시 60.
RATE_LIMIT_RPM = _int("RATE_LIMIT_RPM", 60)
if RATE_LIMIT_RPM < 0:
    RATE_LIMIT_RPM = 0  # 0 = 제한 없음으로 통일

# 리소스 보호
MAX_TABLES_PER_REQUEST = _int("MAX_TABLES_PER_REQUEST", 50)
MAX_IDENTIFIER_LENGTH = _int("MAX_IDENTIFIER_LENGTH", 64)
MAX_LIST_TABLES_RESULT = _int("MAX_LIST_TABLES_RESULT", 500)  # 0 = 제한 없음
MAX_CONCURRENT_REQUESTS = _int("MAX_CONCURRENT_REQUESTS", 0)  # 0 = 제한 없음

# 입력 검증: 허용 스키마 화이트리스트. 비어 있으면 모든 스키마 허용.
_allowed = os.getenv("ALLOWED_SCHEMAS", "").strip()
ALLOWED_SCHEMAS: tuple[str, ...] = tuple(s.strip() for s in _allowed.split(",") if s.strip())

# 감사 로그
AUDIT_ENABLED = _bool("AUDIT_ENABLED", True)
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "").strip()  # 비어 있으면 stderr
AUDIT_FORMAT = os.getenv("AUDIT_FORMAT", "json").strip().lower()
if AUDIT_FORMAT not in ("json",):
    AUDIT_FORMAT = "json"
