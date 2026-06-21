"""스키마 로드 모듈 (GitHub YAML 호출을 시뮬레이션)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.config import SCHEMA_DIR

_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.]*$")
_HANGUL_RE = re.compile(r"[가-힣]")


def load_all_schemas(schema_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    data/schemas 아래 모든 YAML 스키마를 로드합니다.

    실제 운영 환경에서는 GitHub API로 동일 형식의 YAML을 받아옵니다.
    """
    base = schema_dir or SCHEMA_DIR
    schemas: List[Dict[str, Any]] = []

    if not base.exists():
        raise FileNotFoundError(f"스키마 디렉터리를 찾을 수 없습니다: {base}")

    for path in sorted(base.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data:
            data["_source_file"] = path.name
            schemas.append(data)

    return schemas


def build_column_description_map(
    schemas: List[Dict[str, Any]],
) -> Dict[str, str]:
    """컬럼명(대문자) → 한글 description 매핑을 생성합니다."""
    mapping: Dict[str, str] = {}
    for schema in schemas:
        for table in schema.get("tables", []):
            for col in table.get("columns", []):
                name = col.get("name", "").upper()
                desc = _clean_column_description(col.get("description", ""))
                if name and desc and name not in mapping:
                    mapping[name] = desc
    return mapping


def _clean_column_description(description: str) -> str:
    """FK 참조 등 괄호 부가 정보를 제거한 한글 설명을 반환합니다."""
    text = description.strip()
    return re.sub(r"\s*\([^)]*\.[^)]*\)\s*$", "", text).strip()


def _is_korean_alias(alias: str) -> bool:
    """한글이 포함된 alias 여부."""
    return bool(_HANGUL_RE.search(alias))


def _format_aliases(aliases: Any, *, exclude_korean: bool = False) -> str:
    if not aliases:
        return ""
    if isinstance(aliases, str):
        items = [aliases]
    else:
        items = [str(a) for a in aliases]

    formatted: List[str] = []
    for alias in items:
        if exclude_korean and _is_korean_alias(alias):
            continue
        formatted.append(_upper_ident(alias))
    return ", ".join(formatted)


def _upper_ident(value: str) -> str:
    """영문 식별자는 대문자로, 한글 등은 그대로 유지합니다."""
    text = str(value)
    if _IDENT_RE.match(text):
        return text.upper()
    if "." in text and all(_IDENT_RE.match(part) for part in text.split(".")):
        return ".".join(part.upper() for part in text.split("."))
    return text


def filtered_tables_to_prompt(tables: List[Dict[str, Any]]) -> str:
    """
    필터된 테이블·컬럼만 압축 형식으로 변환 (ChatGPT 토큰 절약).

    예: HR.EMPLOYEES(EMP_NO NUMBER(3), EMP_NAME VARCHAR2(10))
    """
    lines: List[str] = []
    for table in tables:
        db = _upper_ident(table.get("database", ""))
        tname = _upper_ident(table["name"])
        table_label = f"{db}.{tname}"

        col_parts: List[str] = []
        for col in table.get("columns", []):
            col_name = _upper_ident(col["name"])
            col_parts.append(f"{col_name} {col.get('type', '')}".strip())
        lines.append(f"{table_label}({', '.join(col_parts)})")
    return "\n".join(lines)


def schema_to_text(schema: Dict[str, Any]) -> str:
    """단일 데이터베이스 스키마를 프롬프트용 텍스트로 변환합니다."""
    db_aliases = _format_aliases(schema.get("aliases"))
    lines = [
        f"Database: {schema.get('database', 'unknown')}",
        f"Description: {schema.get('description', '')}",
    ]
    if db_aliases:
        lines.append(f"Aliases: {db_aliases}")
    lines.append("Tables:")

    for table in schema.get("tables", []):
        t_aliases = _format_aliases(table.get("aliases"))
        line = f"  - {table['name']}: {table.get('description', '')}"
        if t_aliases:
            line += f" (aliases: {t_aliases})"
        lines.append(line)
        for col in table.get("columns", []):
            pk = " [PK]" if col.get("primary_key") else ""
            fk = f" [FK -> {col['foreign_key']}]" if col.get("foreign_key") else ""
            c_aliases = _format_aliases(col.get("aliases"))
            col_line = (
                f"      {col['name']} ({col.get('type', '')}){pk}{fk}: "
                f"{col.get('description', '')}"
            )
            if c_aliases:
                col_line += f" (aliases: {c_aliases})"
            lines.append(col_line)
    return "\n".join(lines)
