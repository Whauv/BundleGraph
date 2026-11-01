from pathlib import Path

import pytest

from bundlegraph_app.main import _frontend_directory
from bundlegraph_app.manage import _migration_directory


def test_explicit_migration_directory_requires_sql_files(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no SQL migrations found"):
        _migration_directory({"BUNDLEGRAPH_MIGRATIONS_DIR": str(tmp_path)})

    (tmp_path / "001.sql").write_text("SELECT 1;", encoding="utf-8")
    assert _migration_directory({"BUNDLEGRAPH_MIGRATIONS_DIR": str(tmp_path)}) == tmp_path


def test_explicit_frontend_directory_requires_built_index(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="frontend build not found"):
        _frontend_directory({"BUNDLEGRAPH_FRONTEND_DIRECTORY": str(tmp_path)})

    (tmp_path / "index.html").write_text("<!doctype html>", encoding="utf-8")
    assert _frontend_directory({"BUNDLEGRAPH_FRONTEND_DIRECTORY": str(tmp_path)}) == tmp_path
