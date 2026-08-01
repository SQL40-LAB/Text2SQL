"""MariaDB 연결 및 조회 실행."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

import pandas as pd
import pymysql
from pymysql.cursors import DictCursor

from src.config import (
    MARIADB_DATABASE,
    MARIADB_HOST,
    MARIADB_PASSWORD,
    MARIADB_PORT,
    MARIADB_USER,
    QUERY_PAGE_SIZE,
)


@dataclass
class QueryResult:
    """DB 조회 결과."""

    dataframe: pd.DataFrame = field(default_factory=pd.DataFrame)
    row_count: int = 0
    error: Optional[str] = None
    executed_sql: str = ""


def get_connection():
    """
    [기능: MariaDB 연결]
    로컬 MariaDB에 연결합니다. .env의 MARIADB_* 설정을 사용합니다.
    """
    if not MARIADB_HOST or not MARIADB_USER:
        raise ValueError(
            "MariaDB 연결 정보가 없습니다. .env에 MARIADB_HOST, MARIADB_USER 등을 설정하세요."
        )

    return pymysql.connect(
        host=MARIADB_HOST,
        port=MARIADB_PORT,
        user=MARIADB_USER,
        password=MARIADB_PASSWORD,
        database=MARIADB_DATABASE or None,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


def execute_select(sql: str, *, limit: int = QUERY_PAGE_SIZE) -> QueryResult:
    """
    [기능: SELECT 실행]
    준비된 SQL을 MariaDB에서 실행하고 DataFrame으로 반환합니다.
    안전을 위해 SELECT/WITH 문만 허용하며, 최대 limit건까지 조회합니다.
    """
    result = QueryResult(executed_sql=sql)

    if not sql or not sql.strip():
        result.error = "실행할 SQL이 비어 있습니다."
        return result

    normalized = sql.strip().lstrip("(").lstrip().upper()
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        result.error = "조회 결과 표시는 SELECT(또는 WITH) 문만 지원합니다."
        return result

    # [기능: 행 수 제한] LIMIT이 없으면 상한을 붙여 한 번에 과도한 조회를 막습니다.
    limited_sql = _ensure_limit(sql, limit)

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(limited_sql)
                rows: List[dict[str, Any]] = cursor.fetchall()
        df = pd.DataFrame(rows)
        result.dataframe = df
        result.row_count = len(df)
        result.executed_sql = limited_sql
    except pymysql.Error as e:
        result.error = f"MariaDB 조회 오류: {e}"
    except Exception as e:
        result.error = f"조회 중 오류: {e}"

    return result


def _ensure_limit(sql: str, limit: int) -> str:
    """SQL에 LIMIT이 없으면 끝에 LIMIT n을 추가합니다."""
    stripped = sql.rstrip().rstrip(";")
    if _has_limit(stripped):
        return stripped
    return f"{stripped}\nLIMIT {int(limit)}"


def _has_limit(sql: str) -> bool:
    """이미 LIMIT 절이 있는지 간단히 검사합니다."""
    return bool(re.search(r"\bLIMIT\s+\d+", sql, re.IGNORECASE))
