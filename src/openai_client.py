"""OpenAI ChatGPT API 호출."""

import re

from openai import APIStatusError, AuthenticationError, OpenAI, RateLimitError

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.prompt_builder import SYSTEM_PROMPT, build_user_prompt


class OpenAIConfigurationError(Exception):
    """API 키 미설정 등 설정 오류."""


class OpenAIAPIError(Exception):
    """OpenAI API 호출 실패 (한도, 인증 등)."""


def _extract_error_code(exc: APIStatusError) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error") or {}
        if isinstance(err, dict):
            return str(err.get("code") or err.get("type") or "")
    return ""


def format_openai_exception(exc: Exception) -> str:
    """OpenAI 예외를 사용자용 한국어 메시지로 변환합니다."""
    if isinstance(exc, OpenAIConfigurationError):
        return str(exc)

    if isinstance(exc, AuthenticationError):
        return (
            "OpenAI API 키가 유효하지 않습니다.\n"
            ".env 파일의 OPENAI_API_KEY 값을 확인하세요."
        )

    if isinstance(exc, (RateLimitError, APIStatusError)):
        code = _extract_error_code(exc) if isinstance(exc, APIStatusError) else ""
        message = str(exc)

        if code == "insufficient_quota" or "insufficient_quota" in message:
            return (
                "OpenAI 사용 한도(quota)가 없거나 초과했습니다. "
                "앱 코드 문제가 아니라 계정·결제 설정 문제입니다.\n\n"
                "확인할 항목:\n"
                "• https://platform.openai.com/settings/organization/billing "
                "에서 결제 수단·잔액·사용 한도\n"
                "• 무료 크레딧 만료 여부\n"
                "• .env의 API 키가 사용 중인 조직/프로젝트와 일치하는지\n\n"
                "API 없이 흐름만 테스트하려면 사이드바에서 "
                "「모의 모드 (API 미호출)」를 켜고 다시 시도하세요."
            )

        if isinstance(exc, RateLimitError):
            return (
                "요청이 너무 많아 일시적으로 차단되었습니다(429). "
                "잠시 후 다시 시도하세요."
            )

    return f"OpenAI API 오류: {exc}"


def extract_sql_from_response(content: str) -> str:
    """모델 응답에서 SQL 문자열만 추출합니다."""
    block = re.search(r"```(?:sql)?\s*([\s\S]*?)```", content, re.IGNORECASE)
    if block:
        return block.group(1).strip()
    return content.strip()


def generate_sql(user_query: str, filtered_tables: list) -> tuple[str, str]:
    """
    ChatGPT API를 호출해 SQL을 생성합니다.

    Returns:
        (생성된 SQL, 사용된 사용자 프롬프트)
    """
    user_prompt = build_user_prompt(user_query, filtered_tables)
    sql = generate_sql_from_prompt(user_prompt)
    return sql, user_prompt


def generate_sql_from_prompt(user_prompt: str) -> str:
    """생성된 사용자 프롬프트로 ChatGPT API를 호출해 SQL을 반환합니다."""
    if not OPENAI_API_KEY:
        raise OpenAIConfigurationError(
            "OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요."
        )

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
    except Exception as e:
        raise OpenAIAPIError(format_openai_exception(e)) from e

    raw = response.choices[0].message.content or ""
    return extract_sql_from_response(raw)
