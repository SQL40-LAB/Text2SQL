"""Text2SQL 전체 처리 파이프라인."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.keyword_filter import filter_tables_and_tokens, group_tables_by_database
from src.openai_client import OpenAIAPIError, format_openai_exception, generate_sql_from_prompt
from src.prompt_builder import build_user_prompt
from src.schema_loader import (
    build_column_description_map,
    filtered_tables_to_prompt,
    load_all_schemas,
)
from src.sql_validator import annotate_sql_with_descriptions, format_sql, validate_sql

ProgressCallback = Callable[[int], None]

# progress bar에서 각 단계가 최소 표시되는 시간(초)
MIN_STEP_DISPLAY_SECONDS = 1.0

@dataclass
class Text2SQLResult:
    """파이프라인 실행 결과."""

    sql: str = ""
    success: bool = False
    validation_message: str = ""
    filtered_schemas: List[Dict[str, Any]] = field(default_factory=list)
    filtered_schema_text: str = ""
    prompt_preview: str = ""
    error: Optional[str] = None
    no_matching_tables: bool = False
    filter_tokens: List[str] = field(default_factory=list)


def _make_throttled_progress(
    callback: Optional[ProgressCallback],
    min_seconds: float = MIN_STEP_DISPLAY_SECONDS,
) -> Optional[ProgressCallback]:
    """각 단계가 최소 min_seconds 동안 화면에 표시되도록 콜백을 래핑합니다."""
    if callback is None:
        return None

    last_shown_at: list[Optional[float]] = [None]

    def throttled(completed_count: int) -> None:
        now = time.time()
        if last_shown_at[0] is not None:
            elapsed = now - last_shown_at[0]
            if elapsed < min_seconds:
                time.sleep(min_seconds - elapsed)
        callback(completed_count)
        last_shown_at[0] = time.time()

    return throttled


def _notify_progress(callback: Optional[ProgressCallback], completed_count: int) -> None:
    if callback:
        callback(completed_count)


def run_text2sql(
    user_query: str,
    *,
    use_mock: bool = False,
    on_progress: Optional[ProgressCallback] = None,
) -> Text2SQLResult:
    """
    흐름도 1~8단계를 순서대로 실행합니다.

    1. 사용자 질의
    2~3. 스키마 로드 (GitHub 대신 로컬 YAML)
    4. 키워드 필터링
    5~6. 프롬프트 생성 및 ChatGPT 호출
    7. SQL 파서 검증
    8. 결과 반환
    """
    result = Text2SQLResult()

    if not user_query.strip():
        result.error = "질의 내용을 입력해 주세요."
        return result

    try:
        progress = _make_throttled_progress(on_progress)
        _notify_progress(progress, 0)
        all_schemas = load_all_schemas()
        _notify_progress(progress, 1)

        filtered_tables, result.filter_tokens = filter_tables_and_tokens(
            all_schemas, user_query
        )
        result.filtered_schemas = group_tables_by_database(filtered_tables)
        result.filtered_schema_text = filtered_tables_to_prompt(filtered_tables)
        _notify_progress(progress, 2)

        if not filtered_tables:
            result.no_matching_tables = True
            result.error = (
                "입력하신 질의와 관련된 테이블을 찾을 수 없습니다. "
                "질의에 테이블·컬럼 관련 키워드(예: 부서, 사원, 급여)를 포함해 다시 시도해 주세요."
            )
            return result

        prompt = build_user_prompt(user_query, filtered_tables)
        result.prompt_preview = prompt
        _notify_progress(progress, 3)

        if use_mock:
            sql = _mock_sql(user_query, filtered_tables)
        else:
            sql = generate_sql_from_prompt(prompt)
        _notify_progress(progress, 4)

        ok, msg = validate_sql(sql)
        result.validation_message = msg
        column_descriptions = build_column_description_map(all_schemas)

        if ok:
            formatted_sql = format_sql(sql)
            result.sql = annotate_sql_with_descriptions(
                formatted_sql, column_descriptions
            )
            result.success = True
        else:
            result.sql = annotate_sql_with_descriptions(sql, column_descriptions)
            result.success = False
            result.error = msg

        _notify_progress(progress, 5)

    except OpenAIAPIError as e:
        result.error = str(e)
        result.success = False
    except Exception as e:
        result.error = format_openai_exception(e)
        result.success = False

    return result


def _mock_sql(user_query: str, tables: list) -> str:
    """API 키 없이 UI·로직 테스트용 예시 SQL."""
    if not tables:
        return f"-- 모의 생성 (질의: {user_query[:50]})\nSELECT 1;"
    t = tables[0]
    cols = [c["name"].upper() for c in t.get("columns", [])[:5]]
    col_sql = ", ".join(cols) if cols else "*"
    db = t["database"].upper()
    tname = t["name"].upper()
    return (
        f"-- 모의 생성 (질의: {user_query[:50]})\n"
        f"SELECT {col_sql}\nFROM {db}.{tname}\nFETCH FIRST 10 ROWS ONLY;"
    )
