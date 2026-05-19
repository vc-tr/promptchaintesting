"""SQLite-backed trace logger: one row per agent step."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class TraceStep:
    run_id: str
    step_idx: int
    kind: str  # "llm_call" | "tool_call" | "observation" | "final"
    payload: dict[str, Any]
    latency_ms: float
    input_tokens: int
    output_tokens: int


class TraceLogger:
    def __init__(self, db_path: str = ".traces/agent.db") -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                step_idx INTEGER NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def log(self, step: TraceStep) -> None:
        self._conn.execute(
            """INSERT INTO traces (run_id, step_idx, kind, payload, latency_ms,
               input_tokens, output_tokens) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                step.run_id,
                step.step_idx,
                step.kind,
                json.dumps(step.payload),
                step.latency_ms,
                step.input_tokens,
                step.output_tokens,
            ),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> list[TraceStep]:
        cursor = self._conn.execute(
            "SELECT run_id, step_idx, kind, payload, latency_ms, input_tokens, output_tokens "
            "FROM traces WHERE run_id = ? ORDER BY step_idx",
            (run_id,),
        )
        return [
            TraceStep(
                run_id=row[0],
                step_idx=row[1],
                kind=row[2],
                payload=json.loads(row[3]),
                latency_ms=row[4],
                input_tokens=row[5],
                output_tokens=row[6],
            )
            for row in cursor.fetchall()
        ]

    def close(self) -> None:
        self._conn.close()


@contextmanager
def timed() -> Iterator[dict[str, float]]:
    timing: dict[str, float] = {}
    start = time.perf_counter()
    yield timing
    timing["elapsed_ms"] = (time.perf_counter() - start) * 1000


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]
