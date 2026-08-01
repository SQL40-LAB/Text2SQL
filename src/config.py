"""애플리케이션 설정."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 (src의 상위)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 임시 스키마 YAML 디렉터리 (실서비스에서는 GitHub API로 대체)
SCHEMA_DIR = PROJECT_ROOT / "data" / "schemas"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# 생성·검증에 사용할 SQL 방언 (sqlglot dialect 이름)
SQL_DIALECT = os.getenv("SQL_DIALECT", "oracle")

# --- MariaDB 연결 (로컬 조회용) ---
MARIADB_HOST = os.getenv("MARIADB_HOST", "127.0.0.1")
MARIADB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
MARIADB_USER = os.getenv("MARIADB_USER", "root")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "hr")

# 조회 결과 그리드: 한 페이지당 최대 행 수
QUERY_PAGE_SIZE = int(os.getenv("QUERY_PAGE_SIZE", "100"))
