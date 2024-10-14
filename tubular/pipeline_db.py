import threading
import sqlite3
import os

from tubular.enums import PipelineStatus

# yapf: disable
META_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta
(
    next_run INTEGER
)
"""

META_INIT = """
INSERT INTO meta (next_run) VALUES (1)
"""

META_GET_NEXT_ID = """
UPDATE
    meta
SET
    next_run = next_run + 1
RETURNING
    next_run
"""


RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs
(
    run INTEGER,
    start_ts INTEGER,
    duration_ms INTEGER,
    status INTEGER
)
"""

RUNS_ADD = """
INSERT INTO runs
    (run, start_ts, duration_ms, status)
VALUES
    (:run, :start_ts, :duration_ms, :status)
"""

RUNS_GET_NUM = """
SELECT COUNT(*) FROM runs
"""

RUNS_DROP_OLDEST = """
DELETE FROM 
  runs
WHERE
  rowid = (SELECT rowid FROM runs order by rowid limit :count)
"""
# yapf: enable


def lock(func):
    """
    Decorator to automatically lock the object's mutex
    """

    def wrapper(self, *args, **kwargs):
        with self._lock:
            func(self, *args, **kwargs)

    return wrapper


class PipelineDB:

    def __init__(self, path: str) -> None:
        self._path = path
        self._refs = 0
        self._lock = threading.Semaphore()

        initDB = not os.path.exists(path)

        self._dbCon = sqlite3.connect(path)
        self._dbCur = self._dbCon.cursor()

        if initDB:
            self._dbCur.execute(META_SCHEMA)
            self._dbCur.execute(META_INIT)
            self._dbCur.execute(RUNS_SCHEMA)
            self._dbCon.commit()

    @lock
    def getNextRunNum(self) -> int:
        res = self._dbCur.execute(META_GET_NEXT_ID)
        out = res.fetchone()[0][0]
        res.close()
        self._dbCon.commit()
        return out

    @lock
    def addRun(self, runNum: int, start: float, duration: float,
               status: PipelineStatus, maxRuns: int):
        values = {
            "run": runNum,
            "start_ts": int(start),
            "duration_ms": int(duration * 1000),
            "status": status.value
        }

        self._dbCur.execute(RUNS_ADD, values)

        if maxRuns > 0:
            res = self._dbCur.execute(RUNS_GET_NUM)
            count = res.fetchone()[0]
            res.close()
            if count > maxRuns:
                values = {"count": count - maxRuns}
                self._dbCur.execute(RUNS_DROP_OLDEST, values)

        self._dbCon.commit()


class PipelineDBManager:

    def __init__(self) -> None:
        self._dbs: dict[str, PipelineDB] = {}
        self._lock = threading.Semaphore()

    @lock
    def getDB(self, path: str) -> PipelineDB:
        try:
            out = self._dbs[path]
        except KeyError:
            out = PipelineDB(path)
            self._dbs[path] = out

        out._refs += 1
        return out

    @lock
    def closeDB(self, db: PipelineDB):
        db._refs -= 1
        if db._refs == 0:
            del self._dbs[db._path]


inst = PipelineDBManager()
