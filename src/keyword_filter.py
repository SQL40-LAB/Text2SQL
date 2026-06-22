"""사용자 질의 기반 테이블·컬럼 단위 필터링 (토큰 최소화)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

MIN_TOKEN_LEN = 2

# 한국어 자연어 질의에서 스키마 매칭에 쓰이지 않는 불용어
KOREAN_STOPWORDS = frozenset({
    # 요청·동작
    "조회", "검색", "찾기", "찾아", "보기", "보여", "보여줘", "알려", "알려줘",
    "출력", "작성", "생성", "만들", "만들어", "해줘", "해주", "주세요", "싶어",
    "하고", "해서", "하려", "해", "줘", "주", "좀", "다시", "한번",
    # 조사·접속어
    "에서", "으로", "에게", "까지", "부터", "보다", "처럼", "따라", "대한",
    "관하여", "관련", "대해", "위한", "통한", "같은", "이내", "이상", "이하",
    "사이", "중에", "중", "내", "외", "및", "또는", "그리고",
    # 집계·정렬·수식
    "평균", "합계", "합", "총", "전체", "모든", "각", "최대", "최소", "개수",
    "건수", "명수", "내림", "오름", "순서", "정렬", "기준", "비교", "집계",
    "어떤", "무엇", "얼마", "몇", "가장", "제일", "많이", "적게", "높은", "낮은",
    # 단위·시간 표현
    "개", "명", "건", "원", "년", "월", "일", "시", "분", "초",
    "지난", "이번", "다음", "현재", "당월", "전월", "금월", "금년", "작년", "내년",
    # 일반 명사(스키마와 무관)
    "목록", "리스트", "데이터", "정보", "내용", "결과", "경우", "것", "수", "등",
    "있는", "없는", "하는", "되는", "되어", "이다", "입니다",
})

# 한글 토큰 끝에서 제거할 조사 (긴 접미사 우선)
KOREAN_PARTICLE_SUFFIXES = (
    "으로",
    "에서",
    "에게",
    "한테",
    "부터",
    "까지",
    "처럼",
    "보다",
    "과",
    "와",
    "은",
    "는",
    "을",
    "를",
    "이",
    "가",
    "의",
    "에",
    "로",
    "도",
    "만",
    "께",
    "별",
)

# 한글 토큰 끝에서 제거할 요청·동사 어미 (조회해줘 → 조회)
KOREAN_REQUEST_SUFFIXES = (
    "해주세요",
    "해줘",
    "해주",
    "해",
    "줘",
)


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


def _strip_trailing_particles(token: str) -> str:
    """한글 토큰 끝에 붙은 조사를 반복 제거합니다. (예: 부서를 → 부서)"""
    if not re.fullmatch(r"[가-힣]+", token):
        return token

    result = token
    min_stem_len = MIN_TOKEN_LEN

    while True:
        stripped = False
        for suffix in KOREAN_PARTICLE_SUFFIXES:
            if result.endswith(suffix) and len(result) - len(suffix) >= min_stem_len:
                result = result[: -len(suffix)]
                stripped = True
                break
        if not stripped:
            break

    return result


def _strip_request_suffixes(token: str) -> str:
    """한글 토큰 끝의 요청·동사 어미를 제거합니다. (예: 조회해줘 → 조회)"""
    if not re.fullmatch(r"[가-힣]+", token):
        return token

    result = token
    min_stem_len = MIN_TOKEN_LEN

    while True:
        stripped = False
        for suffix in KOREAN_REQUEST_SUFFIXES:
            if result.endswith(suffix) and len(result) - len(suffix) >= min_stem_len:
                result = result[: -len(suffix)]
                stripped = True
                break
        if not stripped:
            break

    return result


def _normalize_token(part: str) -> str:
    """토큰 정규화: 소문자 변환, 조사·요청 어미 제거."""
    token = part.lower()
    if re.fullmatch(r"[가-힣]+", token):
        token = _strip_trailing_particles(token)
        token = _strip_request_suffixes(token)
    return token


def _tokenize_query(query: str) -> Set[str]:
    normalized = query.lower().strip()
    tokens: Set[str] = set()
    for part in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[가-힣]+|\d+", normalized):
        token = _normalize_token(part)
        if len(token) >= MIN_TOKEN_LEN:
            tokens.add(token)
    return _remove_stopwords(tokens)


def _remove_stopwords(tokens: Set[str]) -> Set[str]:
    """한국어 불용어를 제거해 스키마 매칭 노이즈를 줄입니다."""
    return {token for token in tokens if token not in KOREAN_STOPWORDS}


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


def extract_query_tokens(query: str) -> List[str]:
    """질의에서 스키마 매칭에 사용된 토큰 목록을 반환합니다."""
    return sorted(_tokenize_query(query))


def format_query_with_highlighted_tokens(query: str, tokens: List[str]) -> str:
    """질의문에서 매칭에 사용된 토큰 어간만 하이라이트한 HTML을 반환합니다."""
    if not query or not tokens:
        return query

    token_set = {token.lower() for token in tokens}
    mark_open = (
        '<mark style="background-color:#fff3bf;'
        'padding:0 4px;border-radius:4px;font-weight:600;">'
    )
    mark_close = "</mark>"
    parts: List[str] = []
    last = 0

    for match in re.finditer(r"[a-zA-Z_][a-zA-Z0-9_]*|[가-힣]+|\d+", query):
        parts.append(query[last : match.start()])
        segment = match.group()
        normalized = _normalize_token(segment)

        if normalized in token_set:
            segment_lower = segment.lower()
            if segment_lower.startswith(normalized):
                stem = segment[: len(normalized)]
                remainder = segment[len(normalized) :]
                parts.append(f"{mark_open}{stem}{mark_close}{remainder}")
            else:
                parts.append(f"{mark_open}{segment}{mark_close}")
        else:
            parts.append(segment)
        last = match.end()

    parts.append(query[last:])
    return "".join(parts)


def filter_tables_and_tokens(
    schemas: List[Dict[str, Any]], query: str
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    스키마 필터링 결과와 질의에서 추출한 토큰 목록을 함께 반환합니다.

    Returns:
        (filtered_tables, query_tokens)
    """
    query_tokens = extract_query_tokens(query)
    if not query_tokens:
        return [], query_tokens

    tokens = _expand_tokens_from_schemas(set(query_tokens), schemas)

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
        return [], query_tokens

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

    return result, query_tokens


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
    tables, _ = filter_tables_and_tokens(schemas, query)
    return tables


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
