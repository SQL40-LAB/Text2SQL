"""사용자 질의 기반 테이블·컬럼 단위 필터링 (토큰 최소화)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

MIN_TOKEN_LEN = 2


def _normalize_aliases(aliases: Any) -> List[str]:
    if not aliases:
        return []
    if isinstance(aliases, str):
        return [aliases]
    return [str(a) for a in aliases]


def _entity_terms(
    name: str, description: str = "", aliases: Any = None
) -> List[str]:
    terms = [name]
    if description:
        terms.append(description)
    terms.extend(_normalize_aliases(aliases))
    return [t.lower() for t in terms if t]


def _tokenize_query(query: str) -> Set[str]:
    normalized = query.lower().strip()
    tokens: Set[str] = set()
    for part in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[가-힣]+|\d+", normalized):
        if len(part) >= MIN_TOKEN_LEN:
            tokens.add(part)
    return tokens


def _exact_match(tokens: Set[str], term: str) -> bool:
    return term.lower() in tokens


def _prefix_match(tokens: Set[str], term: str) -> bool:
    """질의 토큰이 엔티티명·별칭으로 시작할 때만 매칭 (예: 부서별 → 부서)."""
    tl = term.lower()
    if len(tl) < MIN_TOKEN_LEN:
        return False
    return any(t.startswith(tl) for t in tokens)


def _matches_entity(tokens: Set[str], terms: List[str], *, allow_prefix: bool) -> bool:
    for term in terms:
        if _exact_match(tokens, term):
            return True
        if allow_prefix and _prefix_match(tokens, term):
            return True
    return False


def _table_matches(table: Dict[str, Any], tokens: Set[str]) -> bool:
    terms = _entity_terms(
        table["name"],
        table.get("description", ""),
        table.get("aliases"),
    )
    return _matches_entity(tokens, terms, allow_prefix=True)


def _column_matches(col: Dict[str, Any], tokens: Set[str]) -> bool:
    """컬럼은 name·aliases만 비교 (description 제외, 부분 포함 매칭 없음)."""
    terms = _entity_terms(col["name"], "", col.get("aliases"))
    return _matches_entity(tokens, terms, allow_prefix=False)


def _expand_tokens_from_schemas(tokens: Set[str], schemas: List[Dict[str, Any]]) -> Set[str]:
    """매칭된 테이블·컬럼의 영문명 등을 토큰에 보강합니다."""
    expanded = set(tokens)

    def _add_entity_tokens(name: str, aliases: Any) -> None:
        expanded.add(name.lower())
        for alias in _normalize_aliases(aliases):
            expanded.add(alias.lower())

    for schema in schemas:
        for table in schema.get("tables", []):
            if _table_matches(table, tokens):
                _add_entity_tokens(table["name"], table.get("aliases"))

            for col in table.get("columns", []):
                if _column_matches(col, tokens):
                    _add_entity_tokens(col["name"], col.get("aliases"))

    return expanded


def _slim_column(col: Dict[str, Any]) -> Dict[str, Any]:
    """프롬프트용 최소 컬럼 정보 (긴 description 제외)."""
    slim: Dict[str, Any] = {
        "name": col["name"],
        "type": col.get("type", ""),
    }
    if col.get("primary_key"):
        slim["primary_key"] = True
    if col.get("foreign_key"):
        slim["foreign_key"] = col["foreign_key"]
    if col.get("aliases"):
        slim["aliases"] = col["aliases"]
    return slim


def _score_column(col: Dict[str, Any], tokens: Set[str]) -> int:
    return 3 if _column_matches(col, tokens) else 0


def _collect_columns_for_table(
    table: Dict[str, Any],
    tokens: Set[str],
    table_matched: bool,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    필터에 포함된 테이블의 **모든 컬럼**을 프롬프트용으로 반환합니다.
    테이블 선정은 질의 매칭으로 하고, 컬럼은 전체를 포함합니다.
    """
    score = 2 if table_matched else 0
    columns: List[Dict[str, Any]] = []

    for col in table.get("columns", []):
        score += _score_column(col, tokens)
        columns.append(_slim_column(col))

    return columns, score


def filter_tables_by_query(
    schemas: List[Dict[str, Any]], query: str
) -> List[Dict[str, Any]]:
    """
    스키마(DB) 단위가 아닌 **테이블·컬럼 단위**로 필터링합니다.

    테이블 포함 기준:
    - 테이블 name·description·aliases가 질의와 정확히 일치하거나
      질의 토큰이 해당 명칭으로 시작하는 경우 (예: 부서별 → 부서)
    - 컬럼 name·aliases가 질의와 정확히 일치하는 경우

    포함된 테이블은 **모든 컬럼**을 프롬프트에 전달합니다.

    Returns:
        [{"database": "hr", "name": "employees", "columns": [slim, ...]}, ...]
    """
    tokens = _tokenize_query(query)
    if not tokens:
        return []

    tokens = _expand_tokens_from_schemas(tokens, schemas)

    candidates: List[Tuple[int, str, Dict[str, Any], bool]] = []

    for schema in schemas:
        database = schema.get("database", "unknown")
        for table in schema.get("tables", []):
            table_matched = _table_matches(table, tokens)

            col_score_sum = sum(
                _score_column(c, tokens) for c in table.get("columns", [])
            )

            if not table_matched and col_score_sum == 0:
                continue

            total_score = col_score_sum + (2 if table_matched else 0)
            candidates.append((total_score, database, table, table_matched))

    if not candidates:
        return []

    candidates.sort(key=lambda x: x[0], reverse=True)

    result: List[Dict[str, Any]] = []
    for _, database, table, table_matched in candidates:
        columns, _ = _collect_columns_for_table(table, tokens, table_matched)
        if not columns:
            continue
        result.append(
            {
                "database": database,
                "name": table["name"],
                "description": table.get("description", ""),
                "aliases": table.get("aliases", []),
                "columns": columns,
            }
        )

    return result


def group_tables_by_database(
    tables: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_db: Dict[str, List[Dict[str, Any]]] = {}
    for t in tables:
        by_db.setdefault(t["database"], []).append(
            {"name": t["name"], "columns": t["columns"]}
        )

    return [
        {"database": db, "tables": tbls}
        for db, tbls in by_db.items()
    ]


def filter_schemas_by_query(
    schemas: List[Dict[str, Any]], query: str
) -> List[Dict[str, Any]]:
    """UI 호환용: 필터된 테이블을 DB별로 묶어 반환합니다."""
    return group_tables_by_database(filter_tables_by_query(schemas, query))
