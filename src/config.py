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
