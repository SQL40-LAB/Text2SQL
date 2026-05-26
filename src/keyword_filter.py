"""사용자 질의 기반 테이블·컬럼 단위 필터링 (토큰 최소화)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

MIN_TOKEN_LEN = 2
# 프롬프트에 넣을 최대 테이블 수 (질의와 무관한 DB 전체 포함 방지)
MAX_TABLES = 4


def _normalize_aliases(aliases: Any) -> List[str]:
    if not aliases:
        return []
    if isinstance(aliases, str):
        return [aliases]
    return [str(a) for a in aliases]


def _build_search_text(
    name: str, description: str = "", aliases: Any = None, extra: str = ""
) -> str:
    parts = [name, description or "", extra or ""]
    parts.extend(_normalize_aliases(aliases))
    return " ".join(p for p in parts if p).lower()


def _tokenize_query(query: str) -> Set[str]:
    normalized = query.lower().strip()
    tokens: Set[str] = set()
    for part in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[가-힣]+|\d+", normalized):
        if len(part) >= MIN_TOKEN_LEN:
            tokens.add(part)
    return tokens


def _expand_tokens_from_schemas(tokens: Set[str], schemas: List[Dict[str, Any]]) -> Set[str]:
    expanded = set(tokens)

    def _alias_hits(alias: str, query_tokens: Set[str]) -> bool:
        alias_lower = alias.lower()
        if len(alias_lower) < MIN_TOKEN_LEN:
            return False
        for t in query_tokens:
            if t == alias_lower or t in alias_lower or alias_lower in t:
                return True
        return False

    def _add_entity_tokens(name: str, aliases: Any) -> None:
        expanded.add(name.lower())
        for a in _normalize_aliases(aliases):
            expanded.add(a.lower())

    for schema in schemas:
        for table in schema.get("tables", []):
            if _alias_hits(table["name"], tokens) or any(
                _alias_hits(a, tokens) for a in _normalize_aliases(table.get("aliases"))
            ):
                _add_entity_tokens(table["name"], table.get("aliases"))

            for col in table.get("columns", []):
                if _alias_hits(col["name"], tokens) or any(
                    _alias_hits(a, tokens) for a in _normalize_aliases(col.get("aliases"))
                ):
                    _add_entity_tokens(col["name"], col.get("aliases"))

    return expanded


def _text_matches(search_text: str, tokens: Set[str]) -> bool:
    return any(t in search_text for t in tokens if len(t) >= MIN_TOKEN_LEN)


def _fk_target_table(foreign_key: str) -> Optional[str]:
    """'departments.dept_id' → 'departments'"""
    if not foreign_key or "." not in foreign_key:
        return None
    return foreign_key.split(".", 1)[0].strip().lower()


def _slim_column(col: Dict[str, Any]) -> Dict[str, Any]:
    """프롬프트용 최소 컬럼 정보 (aliases·긴 description 제외)."""
    slim: Dict[str, Any] = {
        "name": col["name"],
        "type": col.get("type", ""),
    }
    if col.get("primary_key"):
        slim["primary_key"] = True
    if col.get("foreign_key"):
        slim["foreign_key"] = col["foreign_key"]
    return slim


def _score_column(col: Dict[str, Any], tokens: Set[str]) -> int:
    col_text = _build_search_text(
        col["name"],
        col.get("description", ""),
        col.get("aliases"),
        col.get("type", ""),
    )
    return 3 if _text_matches(col_text, tokens) else 0


def _collect_columns_for_table(
    table: Dict[str, Any],
    tokens: Set[str],
    table_matched: bool,
    selected_tables: Set[Tuple[str, str]],
    database: str,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    테이블에 포함할 컬럼과 관련도 점수를 반환합니다.
    - 컬럼 직접 매칭만 기본 포함
    - 테이블만 매칭 시 PK·FK만 (전체 컬럼 X)
    - FK는 선택된 다른 테이블을 참조할 때만 추가
    """
    matched_cols: List[Dict[str, Any]] = []
    seen_names: Set[str] = set()
    score = 0

    table_key = (database.lower(), table["name"].lower())

    for col in table.get("columns", []):
        col_score = _score_column(col, tokens)
        if col_score > 0:
            score += col_score
            if col["name"] not in seen_names:
                matched_cols.append(_slim_column(col))
                seen_names.add(col["name"])

    if table_matched:
        score += 2

    # PK·조인용 FK만 보강 (전체 컬럼 로드하지 않음)
    for col in table.get("columns", []):
        name = col["name"]
        if name in seen_names:
            continue

        if col.get("primary_key"):
            matched_cols.append(_slim_column(col))
            seen_names.add(name)
            continue

        fk = col.get("foreign_key")
        if fk:
            target = _fk_target_table(fk)
            if target and (database.lower(), target) in selected_tables:
                matched_cols.append(_slim_column(col))
                seen_names.add(name)

    return matched_cols, score


def filter_tables_by_query(
    schemas: List[Dict[str, Any]], query: str
) -> List[Dict[str, Any]]:
    """
    스키마(DB) 단위가 아닌 **테이블·컬럼 단위**로 필터링합니다.

    Returns:
        [{"database": "hr", "name": "employees", "columns": [slim, ...]}, ...]
    """
    tokens = _tokenize_query(query)
    if not tokens:
        return _fallback_tables(schemas, limit=1)

    tokens = _expand_tokens_from_schemas(tokens, schemas)

    # 1차: 테이블별 관련도 수집 (DB 전체 포함 없음)
    candidates: List[Tuple[int, str, Dict[str, Any], bool]] = []

    for schema in schemas:
        database = schema.get("database", "unknown")
        for table in schema.get("tables", []):
            table_text = _build_search_text(
                table["name"],
                table.get("description", ""),
                table.get("aliases"),
            )
            table_matched = _text_matches(table_text, tokens)

            col_score_sum = sum(
                _score_column(c, tokens) for c in table.get("columns", [])
            )

            if not table_matched and col_score_sum == 0:
                continue

            total_score = col_score_sum + (2 if table_matched else 0)
            candidates.append((total_score, database, table, table_matched))

    if not candidates:
        return _fallback_tables(schemas, limit=1)

    candidates.sort(key=lambda x: x[0], reverse=True)
    top = candidates[:MAX_TABLES]

    selected_keys: Set[Tuple[str, str]] = {
        (db.lower(), t["name"].lower()) for _, db, t, _ in top
    }

    result: List[Dict[str, Any]] = []
    for _, database, table, table_matched in top:
        columns, _ = _collect_columns_for_table(
            table, tokens, table_matched, selected_keys, database
        )
        if not columns:
            continue
        result.append(
            {
                "database": database,
                "name": table["name"],
                "columns": columns,
            }
        )

    if not result:
        return _fallback_tables(schemas, limit=1)

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


def _fallback_tables(
    schemas: List[Dict[str, Any]], limit: int = 1
) -> List[Dict[str, Any]]:
    """매칭 실패 시: 테이블 1개 + PK만 (토큰 최소)."""
    for schema in schemas:
        database = schema.get("database", "unknown")
        for table in schema.get("tables", [])[:limit]:
            pk_cols = [
                _slim_column(c)
                for c in table.get("columns", [])
                if c.get("primary_key")
            ]
            if pk_cols:
                return [
                    {
                        "database": database,
                        "name": table["name"],
                        "columns": pk_cols[:3],
                    }
                ]
    return []
