"""Transaction helpers for coordinated persistence."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Tuple
from uuid import uuid4

import sqlite3

from ..runtime.logging import get_logger

_LOGGER = get_logger("data_storage.transactions")

def _savepoint_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"

@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    use_savepoint = conn.in_transaction
    savepoint = _savepoint_name("tx_guard")
    if use_savepoint:
        conn.execute(f"SAVEPOINT {savepoint}")
    else:
        conn.execute("BEGIN")
    try:
        yield conn
        if use_savepoint:
            conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        else:
            conn.commit()
    except Exception:
        if use_savepoint:
            conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        else:
            conn.rollback()
        raise


@contextmanager
def transaction_pair(
    core_conn: sqlite3.Connection,
    artifact_conn: sqlite3.Connection,
) -> Iterator[Tuple[sqlite3.Connection, sqlite3.Connection]]:
    core_savepoint = _savepoint_name("core_pair_tx")
    artifact_savepoint = _savepoint_name("artifact_pair_tx")
    core_in_tx = core_conn.in_transaction
    artifact_in_tx = artifact_conn.in_transaction
    if core_in_tx:
        core_conn.execute(f"SAVEPOINT {core_savepoint}")
    else:
        core_conn.execute("BEGIN")
    if artifact_in_tx:
        artifact_conn.execute(f"SAVEPOINT {artifact_savepoint}")
    else:
        artifact_conn.execute("BEGIN")
    core_committed = False
    artifact_committed = False
    try:
        yield core_conn, artifact_conn
        try:
            if core_in_tx:
                core_conn.execute(f"RELEASE SAVEPOINT {core_savepoint}")
            else:
                core_conn.commit()
            core_committed = True
            if artifact_in_tx:
                artifact_conn.execute(f"RELEASE SAVEPOINT {artifact_savepoint}")
            else:
                artifact_conn.commit()
            artifact_committed = True
        except Exception:
            if core_committed != artifact_committed:
                _LOGGER.critical(
                    "Partial transaction commit detected: core=%s artifact=%s",
                    core_committed,
                    artifact_committed,
                )
            raise
    except Exception:
        if core_in_tx:
            core_conn.execute(f"ROLLBACK TO SAVEPOINT {core_savepoint}")
            core_conn.execute(f"RELEASE SAVEPOINT {core_savepoint}")
        elif core_conn.in_transaction:
            core_conn.rollback()
        if artifact_in_tx:
            artifact_conn.execute(f"ROLLBACK TO SAVEPOINT {artifact_savepoint}")
            artifact_conn.execute(f"RELEASE SAVEPOINT {artifact_savepoint}")
        elif artifact_conn.in_transaction:
            artifact_conn.rollback()
        raise
