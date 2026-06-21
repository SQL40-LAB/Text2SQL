"""SQL 파서 기반 검증."""

import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from src.config import SQL_DIALECT


class SQLValidationError(Exception):
    """SQL 구문 검증 실패."""


def validate_sql(sql: str, dialect: str = SQL_DIALECT) -> tuple[bool, str]:
    """
    sqlglot으로 SQL 구문을 검증합니다.

    Returns:
        (성공 여부, 메시지)
    """
    if not sql or not sql.strip():
        return False, "SQL이 비어 있습니다."

    try:
        statements = sqlglot.parse(sql, read=dialect)
    except ParseError as e:
        return False, f"구문 오류: {e}"

    if not statements or all(s is None for s in statements):
        return False, "파싱할 수 있는 SQL 문이 없습니다."

    for stmt in statements:
        if stmt is None:
            continue
        # 허용되는 최상위 문 타입
        if not isinstance(
            stmt,
            (
                exp.Select,
                exp.Insert,
                exp.Update,
                exp.Delete,
                exp.Create,
                exp.Union,
            ),
        ):
            return False, f"지원하지 않거나 확인이 필요한 문 유형: {type(stmt).__name__}"

    return True, f"SQL 구문 검증을 통과했습니다. (dialect: {dialect})"


def format_sql(sql: str, dialect: str = SQL_DIALECT) -> str:
    """검증 후 읽기 쉽게 포맷합니다."""
    try:
        return sqlglot.transpile(sql, read=dialect, write=dialect, pretty=True)[0]
    except Exception:
        return sql


def annotate_sql_with_descriptions(
    sql: str, column_descriptions: dict[str, str]
) -> str:
    """
    SQL 각 줄에 등장하는 컬럼명에 대해 한글 description 주석을 줄 끝에 추가합니다.

    예: SELECT SALARY_MONTH → SELECT SALARY_MONTH /* 급여월 */
    """
    if not sql or not column_descriptions:
        return sql

    sorted_columns = sorted(column_descriptions.items(), key=lambda x: len(x[0]), reverse=True)
    annotated_lines: list[str] = []

    for line in sql.splitlines():
        stripped = line.rstrip()
        if not stripped.strip() or stripped.strip().startswith("--"):
            annotated_lines.append(line)
            continue

        code_part = _strip_trailing_comments(stripped)
        comments: list[str] = []

        for col_name, desc in sorted_columns:
            comment = f"/* {desc} */"
            if comment in stripped:
                continue
            if re.search(rf"\b{re.escape(col_name)}\b", code_part, re.IGNORECASE):
                comments.append(comment)

        if comments:
            annotated_lines.append(f"{stripped} {' '.join(comments)}")
        else:
            annotated_lines.append(line)

    return "\n".join(annotated_lines)


def _strip_trailing_comments(line: str) -> str:
    """줄 끝 블록 주석을 제외한 SQL 본문을 반환합니다."""
    return re.sub(r"/\*.*?\*/", "", line).strip()
