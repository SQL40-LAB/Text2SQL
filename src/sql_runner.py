"""생성된 SQL을 MariaDB에서 실행 가능한 형태로 준비하고 결과를 가공합니다."""

from __future__ import annotations

import io
import re
from typing import Optional, Tuple

import pandas as pd
import sqlglot
from sqlglot.errors import ParseError

from src.config import QUERY_PAGE_SIZE
from src.db_client import QueryResult, execute_select


def strip_sql_comments(sql: str) -> str:
    """
    [기능: SQL 주석 제거]
    UI 표시용으로 붙인 /* 한글명 */ 및 -- 주석을 제거해 실행 가능한 SQL만 남깁니다.
    """
    # 블록 주석 제거
    without_block = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    # 라인 주석 제거
    lines = []
    for line in without_block.splitlines():
        if "--" in line:
            line = line[: line.index("--")]
        lines.append(line)
    cleaned = "\n".join(lines)
    # 빈 줄 정리
    cleaned = re.sub(r"\n\s*\n+", "\n", cleaned).strip()
    return cleaned


def is_select_query(sql: str) -> bool:
    """
    [기능: SELECT 판별]
    주석을 제거한 뒤 SELECT 또는 WITH로 시작하는 조회문인지 확인합니다.
    DML/DDL/DCL 등은 False를 반환합니다.
    """
    cleaned = strip_sql_comments(sql or "").strip()
    if not cleaned:
        return False
    # 선행 괄호/(세미콜론 등) 제거 후 첫 키워드 확인
    normalized = re.sub(r"^[\s(;]+", "", cleaned, flags=re.IGNORECASE)
    return bool(re.match(r"^(WITH|SELECT)\b", normalized, flags=re.IGNORECASE))


def to_mariadb_sql(sql: str, source_dialect: str = "mysql") -> Tuple[str, Optional[str]]:
    """
    [기능: MariaDB(MySQL) SQL 정규화]
    생성된 SQL을 MariaDB에서 실행 가능한 MySQL 방언으로 정리합니다.
    이미 mysql/mariadb이면 주석 제거 후 필요 시 포맷만 맞춥니다.
    """
    cleaned = strip_sql_comments(sql)
    if not cleaned:
        return "", "실행할 SQL이 비어 있습니다."

    read_dialect = "mysql" if source_dialect in ("mysql", "mariadb") else source_dialect
    try:
        converted = sqlglot.transpile(
            cleaned,
            read=read_dialect,
            write="mysql",
            pretty=True,
        )[0]
        if not (converted or "").strip():
            return "", "SQL 문법이 올바르지 않습니다. 쿼리를 확인해 주세요."
        return converted, None
    except ParseError as e:
        return (
            "",
            f"SQL 문법이 올바르지 않습니다. 쿼리를 확인해 주세요.\n{e}",
        )
    except Exception as e:
        return cleaned, f"SQL 방언 변환 경고(원문으로 실행 시도): {e}"


def run_query_from_generated_sql(
    annotated_sql: str,
    *,
    db_user: str,
    db_password: str = "",
    source_dialect: str = "mysql",
    fetch_limit: int = QUERY_PAGE_SIZE * 10,
) -> QueryResult:
    """
    [기능: 생성 SQL 기반 DB 조회]
    1) SELECT 여부 확인 → 2) 주석 제거 → 3) MariaDB 방언 정리 → 4) SELECT 실행
    db_user/db_password: 화면에서 입력한 DB 계정 정보
    fetch_limit: 페이징 전에 DB에서 가져올 최대 행 수(기본 1000)
    """
    if not is_select_query(annotated_sql):
        return QueryResult(
            error="SELECT(또는 WITH)가 아닌 문은 실행하지 않습니다. 생성된 SQL만 표시합니다.",
            executed_sql=strip_sql_comments(annotated_sql),
        )

    if not db_user or not db_user.strip():
        return QueryResult(error="DB 사용자 ID를 입력해 주세요.")

    mariadb_sql, convert_warning = to_mariadb_sql(
        annotated_sql, source_dialect=source_dialect
    )
    if not mariadb_sql:
        return QueryResult(
            error=convert_warning or "실행할 SQL이 비어 있습니다.",
            executed_sql=strip_sql_comments(annotated_sql),
        )

    result = execute_select(
        mariadb_sql,
        user=db_user,
        password=db_password,
        limit=fetch_limit,
    )
    if convert_warning and result.error:
        result.error = f"{convert_warning}\n{result.error}"
    elif convert_warning and not result.error:
        result.executed_sql = f"-- {convert_warning}\n{result.executed_sql}"
    return result


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """
    [기능: Excel 변환]
    DataFrame을 .xlsx 바이트로 변환해 다운로드 버튼에 전달합니다.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="query_result")
    return buffer.getvalue()


def paginate_dataframe(
    df: pd.DataFrame, page: int, page_size: int
) -> Tuple[pd.DataFrame, int, int]:
    """
    [기능: 페이징]
    DataFrame을 page_size 단위로 잘라 현재 페이지 슬라이스와 총 페이지 수를 반환합니다.

    Returns:
        (page_df, total_pages, total_rows)
    """
    total_rows = len(df)
    if total_rows == 0:
        return df, 1, 0

    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total_pages, total_rows
