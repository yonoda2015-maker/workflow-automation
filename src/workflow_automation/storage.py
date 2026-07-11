"""SQLite run-history storage. Every run is recorded, including failed ones —
audit trail, not just a cache."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from workflow_automation.models import RunStatus, WorkflowRunResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_name TEXT NOT NULL,
    status TEXT NOT NULL,
    step_results_json TEXT NOT NULL,
    run_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class RunHistory:
    def __init__(self, db_path: Path) -> None:
        assert db_path.parent.exists(), f"parent dir missing: {db_path.parent}"
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def record(self, result: WorkflowRunResult) -> int:
        step_results_json = json.dumps(
            [
                {
                    "step_id": r.step_id,
                    "status": r.status.value,
                    "output": r.output,
                    "error": r.error,
                }
                for r in result.step_results
            ]
        )
        cur = self._conn.execute(
            "INSERT INTO workflow_runs (workflow_name, status, step_results_json) "
            "VALUES (?, ?, ?)",
            (result.workflow_name, result.status.value, step_results_json),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_runs(self, workflow_name: str | None = None, limit: int = 50) -> list[dict]:
        assert 1 <= limit <= 1000, "limit out of sane range"
        if workflow_name is None:
            cur = self._conn.execute(
                "SELECT id, workflow_name, status, run_at FROM workflow_runs "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        else:
            cur = self._conn.execute(
                "SELECT id, workflow_name, status, run_at FROM workflow_runs "
                "WHERE workflow_name = ? ORDER BY id DESC LIMIT ?",
                (workflow_name, limit),
            )
        return [
            {"id": row[0], "workflow_name": row[1], "status": row[2], "run_at": row[3]}
            for row in cur.fetchall()
        ]

    def count(self, status: RunStatus | None = None) -> int:
        if status is None:
            cur = self._conn.execute("SELECT COUNT(*) FROM workflow_runs")
        else:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM workflow_runs WHERE status = ?", (status.value,)
            )
        return cur.fetchone()[0]

    def close(self) -> None:
        self._conn.close()
