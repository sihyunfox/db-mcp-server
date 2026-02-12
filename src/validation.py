"""입력 검증: 스키마/테이블 식별자 패턴, 길이, 리스트 개수, 화이트리스트."""
import re
from typing import Any

from . import config


class ValidationError(Exception):
    """검증 실패 시 사용. 메시지는 클라이언트에 노출 가능한 수준으로."""
    pass


# MySQL 식별자 허용 문자(영문, 숫자, 언더스코어). 백틱/따옴표·공백·세미콜론 등 차단.
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def validate_schema_name(schema_name: str | None) -> None:
    """스키마명 검증. None은 list_tables 전체 조회용으로 허용."""
    if schema_name is None:
        return
    if not isinstance(schema_name, str):
        raise ValidationError("스키마명은 문자열이어야 합니다.")
    schema_name = schema_name.strip()
    if not schema_name:
        raise ValidationError("스키마명을 입력하세요.")
    if len(schema_name) > config.MAX_IDENTIFIER_LENGTH:
        raise ValidationError(f"스키마명은 {config.MAX_IDENTIFIER_LENGTH}자 이하여야 합니다.")
    if not IDENTIFIER_PATTERN.match(schema_name):
        raise ValidationError("스키마명에 허용되지 않은 문자가 포함되어 있습니다.")
    if config.ALLOWED_SCHEMAS and schema_name not in config.ALLOWED_SCHEMAS:
        raise ValidationError("허용되지 않은 스키마입니다.")


def validate_table_name(table_name: str) -> None:
    """테이블명 검증."""
    if not isinstance(table_name, str):
        raise ValidationError("테이블명은 문자열이어야 합니다.")
    table_name = table_name.strip()
    if not table_name:
        raise ValidationError("테이블명을 입력하세요.")
    if len(table_name) > config.MAX_IDENTIFIER_LENGTH:
        raise ValidationError(f"테이블명은 {config.MAX_IDENTIFIER_LENGTH}자 이하여야 합니다.")
    if not IDENTIFIER_PATTERN.match(table_name):
        raise ValidationError("테이블명에 허용되지 않은 문자가 포함되어 있습니다.")


def validate_table_names_list(table_names: Any) -> list[str]:
    """get_tables_metadata 인자: list[str]인지 검증하고, 각 요소 검증 후 반환."""
    if not isinstance(table_names, list):
        raise ValidationError("테이블 목록은 배열이어야 합니다.")
    if len(table_names) > config.MAX_TABLES_PER_REQUEST:
        raise ValidationError(
            f"한 번에 조회 가능한 테이블 수는 {config.MAX_TABLES_PER_REQUEST}개 이하여야 합니다."
        )
    out: list[str] = []
    for i, name in enumerate(table_names):
        if not isinstance(name, str):
            raise ValidationError(f"테이블 목록의 {i + 1}번째 항목이 문자열이 아닙니다.")
        validate_table_name(name)
        out.append(name.strip())
    return out
