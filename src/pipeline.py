"""Text2SQL 전체 처리 파이프라인."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.keyword_filter import filter_tables_by_query, group_tables_by_database
from src.openai_client import OpenAIAPIError, format_openai_exception, generate_sql
from src.schema_loader import filtered_tables_to_prompt, load_all_schemas
from src.sql_validator import format_sql, validate_sql


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


def run_text2sql(user_query: str, *, use_mock: bool = False) -> Text2SQLResult:
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
        all_schemas = load_all_schemas()
        filtered_tables = filter_tables_by_query(all_schemas, user_query)
        result.filtered_schemas = group_tables_by_database(filtered_tables)
        result.filtered_schema_text = filtered_tables_to_prompt(filtered_tables)

        if not filtered_tables:
            result.no_matching_tables = True
            result.error = (
                "입력하신 질의와 관련된 테이블을 찾을 수 없습니다. "
                "질의에 테이블·컬럼 관련 키워드(예: 부서, 사원, 급여)를 포함해 다시 시도해 주세요."
            )
            return result

        if use_mock:
            sql = _mock_sql(user_query, filtered_tables)
            prompt = "(모의 모드 — API 미호출)"
        else:
            sql, prompt = generate_sql(user_query, filtered_tables)

        result.prompt_preview = prompt
        ok, msg = validate_sql(sql)
        result.validation_message = msg

        if ok:
            result.sql = format_sql(sql)
            result.success = True
        else:
            result.sql = sql
            result.success = False
            result.error = msg

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
    cols = [c["name"] for c in t.get("columns", [])[:5]]
    col_sql = ", ".join(cols) if cols else "*"
    return (
        f"-- 모의 생성 (질의: {user_query[:50]})\n"
        f"SELECT {col_sql}\nFROM {t['database']}.{t['name']}\nLIMIT 10;"
    )
