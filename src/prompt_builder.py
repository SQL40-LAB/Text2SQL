"""ChatGPT용 프롬프트 생성."""

from typing import Any, Dict, List

from src.schema_loader import filtered_tables_to_prompt


SYSTEM_PROMPT = """당신은 Oracle SQL 전문가입니다.
사용자의 자연어 요청과 제공된 데이터베이스 스키마만을 근거로 SQL을 작성합니다.

규칙:
1. 제공된 스키마에 존재하는 테이블·컬럼만 사용하세요.
2. 반드시 Oracle SQL 문법으로 작성하세요 (PostgreSQL/MySQL 전용 문법 사용 금지).
3. Oracle 관례를 따르세요. 예: 문자열은 작은따옴표, 날짜는 TO_DATE/TO_TIMESTAMP, 상위 N건은 FETCH FIRST n ROWS ONLY 또는 ROWNUM, 조인은 ANSI JOIN 권장.
4. 응답은 반드시 ```sql ... ``` 코드 블록 하나만 포함하세요. 설명은 최소화하세요.
5. SELECT, INSERT, UPDATE, DELETE 등 사용자 요청에 맞는 문을 생성하세요.
6. 조인이 필요하면 FK 관계를 활용하세요.
"""


def build_user_prompt(
    user_query: str, filtered_tables: List[Dict[str, Any]]
) -> str:
    """필터링된 테이블·컬럼만 담은 압축 프롬프트를 구성합니다."""
    schema_block = filtered_tables_to_prompt(filtered_tables)
    return f"""## 관련 테이블·컬럼 (필터링됨)

{schema_block}

## 사용자 요청

{user_query}

위 테이블·컬럼과 요청에 맞는 **Oracle SQL**을 작성해 주세요.
"""
