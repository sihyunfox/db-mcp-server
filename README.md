# db-mcp-server

MySQL DB 메타데이터를 조회하는 MCP(Model Context Protocol) 서버입니다. DDL 문서 작성을 위해 테이블·컬럼·인덱스·제약 정보를 읽기 전용으로 제공합니다.

- **프레임워크**: FastMCP (Python)
- **DB**: MySQL 5.7+ (8.0 권장), Information Schema만 SELECT
- **처리량 제한**: 분당 Tool 호출 횟수 설정 가능 (기본 60회/분)

## 요구사항

- Python 3.10+
- MySQL 서버 (읽기 전용 계정 권장)

## 설치

### Windows에서 가상환경 만들고 실행

프로젝트 루트(`db-mcp-server`)에서 다음 순서로 실행합니다.

**CMD(명령 프롬프트):**

```cmd
cd d:\Project\db-mcp-server

REM 가상환경 생성
python -m venv .venv

REM 가상환경 활성화
.venv\Scripts\activate.bat

REM 의존성 설치
pip install -r requirements.txt

REM .env 설정 (최초 1회, 예시 복사 후 편집)
copy .env.example .env

REM MCP 서버 실행 (stdio)
python -m src.server
```

**PowerShell:**

```powershell
cd d:\Project\db-mcp-server

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (실행 정책 오류 시: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser)
.venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt

# .env 설정 (최초 1회)
Copy-Item .env.example .env

# MCP 서버 실행
python -m src.server
```

위 단계를 한 번에 실행하는 샘플 스크립트는 [scripts/run-windows.cmd](scripts/run-windows.cmd)를 참고하세요.

### 일반 설치 (이미 가상환경이 있는 경우)

```bash
cd db-mcp-server
pip install -r requirements.txt
```

## 설정

`.env.example`을 복사해 `.env`를 만들고 DB 연결 정보를 입력합니다.

```bash
cp .env.example .env
# .env 편집: DB_HOST, DB_USER, DB_PASSWORD 등
```

| 변수명 | 필수 | 설명 | 기본값 |
|--------|------|------|--------|
| DB_HOST | O | MySQL 호스트 | localhost |
| DB_PORT | | 포트 | 3306 |
| DB_USER | O | DB 사용자(읽기 전용 권장) | - |
| DB_PASSWORD | O | 비밀번호 | - |
| DB_NAME | | 기본 스키마 | - |
| DB_SSL | | SSL 사용 여부 (true/false) | false |
| DB_CONNECT_TIMEOUT | | 연결 타임아웃(초) | 10 |
| DB_QUERY_TIMEOUT | | 쿼리 타임아웃(초) | 30 |
| RATE_LIMIT_RPM | | 분당 최대 Tool 호출 횟수. 0이면 제한 없음 | 60 |
| MAX_TABLES_PER_REQUEST | | get_tables_metadata 한 번에 조회 가능한 테이블 수 상한 | 50 |
| MAX_IDENTIFIER_LENGTH | | 스키마/테이블명 최대 길이(문자) | 64 |
| MAX_LIST_TABLES_RESULT | | list_tables 반환 개수 상한. 0이면 제한 없음 | 500 |
| MAX_CONCURRENT_REQUESTS | | 동시 처리 Tool 호출 수 상한. 0이면 제한 없음 | 0 |
| ALLOWED_SCHEMAS | | 허용 스키마 목록(쉼표 구분). 비어 있으면 전체 허용 | - |
| AUDIT_ENABLED | | 감사 로그 사용 여부 | true |
| AUDIT_LOG_PATH | | 감사 로그 파일 경로. 비어 있으면 stderr | - |
| AUDIT_FORMAT | | 감사 로그 형식 (json) | json |

상세 보안 항목은 [docs/보안_기능_추가_리스트.md](docs/보안_기능_추가_리스트.md) 참고.

## 실행

### stdio (로컬·Cursor 등)

```bash
python -m src.server
```

또는 FastMCP CLI:

```bash
fastmcp run src/server.py:mcp
```

### HTTP (원격·테스트)

특정 포트에서 HTTP로 띄운 뒤 클라이언트/스크립트로 호출할 수 있습니다.

```bash
python -m src.server --http 8000
```

기본 주소: `http://127.0.0.1:8000/mcp`

**HTTP로 ads 테이블 메타데이터 조회 테스트:**

1. 터미널 1에서 서버 실행: `python -m src.server --http 8000`
2. 터미널 2에서 테스트 스크립트 실행:
   ```bash
   python scripts/test_http_ads.py --port 8000 --schema mydb
   ```
   - 스키마를 환경변수로 쓰려면: `set DB_NAME=mydb`(CMD) 후 `python scripts/test_http_ads.py --port 8000`
   - 다른 테이블 조회: `--table 테이블명` 추가

## 제공 도구 (Tools)

| 도구 | 설명 |
|------|------|
| `list_tables` | 스키마별 테이블 목록 (schema_name 선택) |
| `get_table_metadata` | 단일 테이블 DDL용 메타데이터 (테이블/컬럼/PK/UNIQUE/인덱스/FK/CHECK) |
| `get_tables_metadata` | 여러 테이블 메타데이터 일괄 조회 |
| `get_schema_overview` | 스키마 테이블 목록 + FK 관계 요약 |

## Cursor에서 MCP 서버로 추가

1. Cursor 설정에서 MCP(Model Context Protocol) 설정을 엽니다.
2. 서버를 추가하고, 실행 경로를 다음 중 하나로 지정합니다.
   - **명령**: `python` (또는 `uv run python`)
   - **인자**: `-m` `src.server`
   - **작업 디렉터리**: 이 프로젝트 루트(`db-mcp-server`)
3. 또는 `fastmcp run src/server.py:mcp`를 명령으로 사용하고 작업 디렉터리를 프로젝트 루트로 설정합니다.
4. `.env`가 프로젝트 루트에 있어야 합니다.

## 문서

- [요구사항 정의서](docs/요구사항정의서.md)
- [보안 기능 추가 리스트](docs/보안_기능_추가_리스트.md)
