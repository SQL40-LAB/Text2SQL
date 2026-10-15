"""ChatGPT용 프롬프트 생성."""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.schema_loader import filtered_tables_to_prompt

# API에 넣을 최근 질의·SQL 쌍 개수 (토큰 상한)
MAX_SQL_HISTORY_TURNS = 10

ConversationTurn = Tuple[str, str]


SYSTEM_PROMPT = """당신은 MariaDB SQL 전문가입니다.
사용자의 자연어 요청과 제공된 데이터베이스 스키마만을 근거로 SQL을 작성합니다.
이전 질의와 그때 작성한 SQL이 이어져 있으면 대화 맥락으로 활용하세요.
후속 요청(예: "그걸 부서별로", "조건 추가")은 직전 SQL을 수정·확장하세요.

규칙:
1. 제공된 스키마에 존재하는 테이블·컬럼만 사용하세요.
2. 반드시 MariaDB(MySQL 호환) SQL 문법으로 작성하세요 (Oracle/PostgreSQL 전용 문법 사용 금지).
3. MariaDB 관례를 따르세요. 예: 문자열은 작은따옴표, 날짜는 DATE/DATETIME 및 STR_TO_DATE, 상위 N건은 LIMIT n, 조인은 ANSI JOIN 권장. ROWNUM·FETCH FIRST·TO_DATE(Oracle)·dual 등은 사용하지 마세요.
4. 응답은 반드시 ```sql ... ``` 코드 블록 하나만 포함하세요. 설명은 최소화하세요.
5. SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, GRANT 등 사용자 요청에 맞는 문을 생성하세요.
6. 조인이 필요하면 FK 관계를 활용하세요.
7. SQL에 사용하는 스키마명·테이블명·컬럼명은 반드시 대문자로 작성하세요. (예: HR.EMPLOYEES, EMP_NO)
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

위 스키마의 스키마명·테이블명·컬럼명은 모두 대문자로 표기되어 있습니다.
description·aliases는 의미 파악용이며, SQL에는 실제 테이블명·컬럼명만 사용하세요.
요청에 맞는 **MariaDB SQL**을 작성할 때도 동일하게 대문자 식별자를 사용하세요.
이전 질의·SQL이 있으면 그 맥락을 유지한 채 이번 요청을 반영하세요.
"""


def build_chat_messages(
    user_query: str,
    filtered_tables: List[Dict[str, Any]],
    conversation_history: Optional[Sequence[ConversationTurn]] = None,
) -> List[Dict[str, str]]:
    """
    Chat Completions용 messages를 만듭니다.
    system 규칙 → (과거 질의, 과거 SQL) 반복 → 이번 질의(스키마 포함)
    """
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    turns = list(conversation_history or [])
    if MAX_SQL_HISTORY_TURNS > 0:
        turns = turns[-MAX_SQL_HISTORY_TURNS:]
    for past_query, past_sql in turns:
        query = (past_query or "").strip()
        sql = (past_sql or "").strip()
        if not query or not sql:
            continue
        messages.append({"role": "user", "content": query})
        messages.append(
            {"role": "assistant", "content": f"```sql\n{sql}\n```"}
        )
    messages.append(
        {"role": "user", "content": build_user_prompt(user_query, filtered_tables)}
    )
    return messages
