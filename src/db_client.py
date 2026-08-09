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
    MARIADB_PORT,
    QUERY_PAGE_SIZE,
)


@dataclass
class QueryResult:
    """DB 조회 결과."""

    dataframe: pd.DataFrame = field(default_factory=pd.DataFrame)
    row_count: int = 0
    error: Optional[str] = None
    executed_sql: str = ""


def get_connection(*, user: str, password: str = ""):
    """
    [기능: MariaDB 연결]
    Host/Port/Database는 .env 설정을 쓰고,
    사용자 ID·비밀번호는 화면에서 입력받은 값을 사용합니다.
    """
    if not MARIADB_HOST:
        raise ValueError(
            "MariaDB 호스트 정보가 없습니다. .env에 MARIADB_HOST를 설정하세요."
        )
    if not user or not user.strip():
        raise ValueError("DB 사용자 ID를 입력해 주세요.")

    return pymysql.connect(
        host=MARIADB_HOST,
        port=MARIADB_PORT,
        user=user.strip(),
        password=password or "",
        database=MARIADB_DATABASE or None,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


def _format_db_error(exc: Exception) -> str:
    """
    [기능: DB 오류 메시지 변환]
    인증 실패 등 사용자에게 불필요한 기술 메시지를
    이해하기 쉬운 안내로 바꿉니다.
    """
    message = str(exc)
    lower = message.lower()
    errno = getattr(exc, "args", [None])[0] if getattr(exc, "args", None) else None

    auth_keywords = (
        "access denied",
        "authentication",
        "auth_gssapi",
        "using password",
        "password",
        "login",
        "자격",
    )
    auth_errnos = {1045, 1698, 2059, 28000}

    if errno in auth_errnos or any(k in lower for k in auth_keywords):
        return "ID 또는 비밀번호가 다릅니다."

    if errno in {2003, 2002} or "can't connect" in lower or "connection refused" in lower:
        return "DB 서버에 연결할 수 없습니다. 호스트·포트·서버 상태를 확인해 주세요."

    if errno == 1049 or "unknown database" in lower:
        return "데이터베이스 이름이 올바르지 않습니다. .env의 MARIADB_DATABASE를 확인해 주세요."

    return f"MariaDB 조회 오류: {exc}"


def execute_select(
    sql: str,
    *,
    user: str,
    password: str = "",
    limit: int = QUERY_PAGE_SIZE,
) -> QueryResult:
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
        with get_connection(user=user, password=password) as conn:
            with conn.cursor() as cursor:
                cursor.execute(limited_sql)
                rows: List[dict[str, Any]] = cursor.fetchall()
        df = pd.DataFrame(rows)
        result.dataframe = df
        result.row_count = len(df)
        result.executed_sql = limited_sql
    except pymysql.Error as e:
        result.error = _format_db_error(e)
    except Exception as e:
        result.error = _format_db_error(e)

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
