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


def to_mariadb_sql(sql: str, source_dialect: str = "oracle") -> Tuple[str, Optional[str]]:
    """
    [기능: Oracle → MariaDB(MySQL) SQL 변환]
    ChatGPT가 생성한 Oracle SQL을 MariaDB에서 실행 가능한 MySQL 방언으로 변환합니다.
    변환 실패 시 원문(주석 제거본)을 그대로 쓰고 경고 메시지를 반환합니다.
    """
    cleaned = strip_sql_comments(sql)
    if not cleaned:
        return "", "실행할 SQL이 비어 있습니다."

    try:
        converted = sqlglot.transpile(
            cleaned,
            read=source_dialect,
            write="mysql",
            pretty=True,
        )[0]
        return converted, None
    except (ParseError, Exception) as e:
        # 변환 실패해도 주석만 제거한 SQL로 시도할 수 있게 원문을 반환
        return cleaned, f"SQL 방언 변환 경고(원문으로 실행 시도): {e}"


def run_query_from_generated_sql(
    annotated_sql: str,
    *,
    source_dialect: str = "oracle",
    fetch_limit: int = QUERY_PAGE_SIZE * 10,
) -> QueryResult:
    """
    [기능: 생성 SQL 기반 DB 조회]
    1) 주석 제거 → 2) MariaDB 방언 변환 → 3) SELECT 실행
    fetch_limit: 페이징 전에 DB에서 가져올 최대 행 수(기본 1000)
    """
    mariadb_sql, convert_warning = to_mariadb_sql(
        annotated_sql, source_dialect=source_dialect
    )
    if not mariadb_sql:
        result = QueryResult(error=convert_warning or "실행할 SQL이 비어 있습니다.")
        return result

    result = execute_select(mariadb_sql, limit=fetch_limit)
    # 방언 변환에 실패했지만 원문으로 실행을 시도한 경우, 조회 오류에 경고를 함께 표시
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
