import os

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.core.database import Base
from app.models import *  # noqa: F401,F403

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "schema.sql")

HEADER = """-- =============================================================
-- Smart Civic Issue Management System — MySQL Schema
-- =============================================================
-- Auto-generated from backend/app/models/*.py via SQLAlchemy
-- metadata (MySQL dialect). This file is a readable reference
-- and a fallback for environments not using Alembic migrations.
-- The source of truth is the SQLAlchemy models; regenerate this
-- file after any model change rather than hand-editing it.
--
-- Regenerate with:
--   cd backend && python -m app.utils.export_schema
-- =============================================================

CREATE DATABASE IF NOT EXISTS civic_issues_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE civic_issues_db;

"""


def export_schema() -> str:
    statements = []
    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=mysql.dialect())).strip()
        statements.append(ddl + ";")
    return HEADER + "\n\n".join(statements) + "\n"


if __name__ == "__main__":
    sql = export_schema()
    out_path = os.path.abspath(OUTPUT_PATH)
    with open(out_path, "w") as f:
        f.write(sql)
    print(f"Schema exported to {out_path}")
