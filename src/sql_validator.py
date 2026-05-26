"""SQL 파서 기반 검증."""

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
