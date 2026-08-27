"""YAML(org/person/product/customer/contract) 기준 MariaDB 스키마 생성."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQL_PATH = Path(__file__).resolve().parent / "create_insurance_schemas.sql"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create insurance schemas on MariaDB")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3308)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="")
    args = parser.parse_args()

    sql = SQL_PATH.read_text(encoding="utf-8")

    # Prefer official MariaDB CLI (avoids pymysql GSSAPI issues on this host)
    mariadb = Path(r"C:\Program Files\MariaDB 12.3\bin\mariadb.exe")
    if mariadb.exists():
        import subprocess

        cmd = [
            str(mariadb),
            "-h",
            args.host,
            "-P",
            str(args.port),
            "-u",
            args.user,
            f"-p{args.password}" if args.password else f"-p",
            "--binary-mode",
        ]
        # empty -p still prompts; use --password= for empty
        if args.password == "":
            cmd = [
                str(mariadb),
                "-h",
                args.host,
                "-P",
                str(args.port),
                "-u",
                args.user,
                "--password=",
            ]
        else:
            cmd = [
                str(mariadb),
                "-h",
                args.host,
                "-P",
                str(args.port),
                "-u",
                args.user,
                f"--password={args.password}",
            ]

        print("Running:", " ".join(cmd[:6] + ["--password=***"]))
        proc = subprocess.run(
            cmd,
            input=sql.encode("utf-8"),
            capture_output=True,
        )
        sys.stdout.write(proc.stdout.decode("utf-8", errors="replace"))
        sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
        return proc.returncode

    # Fallback: pymysql
    try:
        import pymysql
    except ImportError:
        print("mariadb CLI / pymysql 모두 사용할 수 없습니다.", file=sys.stderr)
        return 1

    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            for stmt in _split_sql(sql):
                cur.execute(stmt)
                if cur.description:
                    rows = cur.fetchall()
                    for row in rows:
                        print(row)
        print("OK: schemas created")
        return 0
    finally:
        conn.close()


def _split_sql(sql: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(buf))
            buf = []
    if buf:
        statements.append("\n".join(buf))
    return statements


if __name__ == "__main__":
    raise SystemExit(main())
