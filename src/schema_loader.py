"""스키마 로드 모듈 (GitHub YAML 호출을 시뮬레이션)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.config import SCHEMA_DIR


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


def _format_aliases(aliases: Any) -> str:
    if not aliases:
        return ""
    if isinstance(aliases, str):
        return aliases
    return ", ".join(str(a) for a in aliases)


def filtered_tables_to_prompt(tables: List[Dict[str, Any]]) -> str:
    """
    필터된 테이블·컬럼만 압축 형식으로 변환 (ChatGPT 토큰 절약).

    예: hr.employees(emp_id INTEGER PK, emp_name VARCHAR, salary DECIMAL)
    """
    lines: List[str] = []
    for table in tables:
        db = table.get("database", "")
        tname = table["name"]
        col_parts: List[str] = []
        for col in table.get("columns", []):
            part = f"{col['name']} {col.get('type', '')}".strip()
            if col.get("primary_key"):
                part += " PK"
            if col.get("foreign_key"):
                part += f" FK->{col['foreign_key']}"
            col_parts.append(part)
        lines.append(f"{db}.{tname}({', '.join(col_parts)})")
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
