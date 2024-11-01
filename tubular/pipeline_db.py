import threading
import sqlite3
import os

from tubular.enums import PipelineStatus

# yapf: disable
PIPELINES_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipelines
(
    id INTEGER PRIMARY KEY,
    path TEXT,
    next_run INTEGER
)
"""

PIPELINES_ADD = """
INSERT INTO
    pipelines
    (path, next_run)
VALUES
    (:path, 1)
RETURNING
    id
"""

# this immediately updates the run value so that we don't
# have any race conditions
PIPELINES_GET_NEXT_RUN = """
UPDATE
    pipelines
SET
    next_run = next_run + 1
WHERE
    path = ?
RETURNING
    id, next_run
"""


RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs
(
    pipeline INTEGER,
    run INTEGER,
    start_ts INTEGER,
    duration_ms INTEGER,
    status INTEGER,
    FOREIGN KEY(pipeline) REFERENCES pipelines(id)
)
"""

RUNS_ADD = """
INSERT INTO runs
    (pipeline, run, start_ts, duration_ms, status)
VALUES
    (:pipeline_id, :run, :start_ts, :duration_ms, :status)
"""

RUNS_GET_NUM_FOR_ID = """
SELECT
    count(*)
FROM
    runs
WHERE
    pipeline = ?
"""

RUNS_DROP_OLDEST = """
DELETE FROM
  runs
WHERE
  rowid = (SELECT rowid FROM runs order by rowid limit :count)
  AND
  pipeline = :pipeline
"""

RUNS_GET_LAST_FOR_PIPELINE = """
SELECT
    run, start_ts, duration_ms, status
FROM
    runs
INNER JOIN
    pipelines
ON
    runs.pipeline = pipelines.id
WHERE
    pipelines.path = ?
ORDER BY
    runs.run DESC
LIMIT 1
"""
# yapf: enable


def lock(func):
    """
    Decorator to automatically lock the object's mutex
    """

    def wrapper(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)

    return wrapper


class PipelineDB:

    def __init__(self, path: str) -> None:
        self._path = path
        self._refs = 0
        self._lock = threading.Semaphore()

        initDB = not os.path.exists(path)

        self._dbCon = sqlite3.connect(path, check_same_thread=False)
        self._dbCur = self._dbCon.cursor()

        if initDB:
            self._dbCur.execute(PIPELINES_SCHEMA)
            self._dbCur.execute(RUNS_SCHEMA)
            self._dbCon.commit()

    @lock
    def getPipelineIDAndNextRun(self, pipelinePath: str) -> tuple[int, int]:
        res = self._dbCur.execute(PIPELINES_GET_NEXT_RUN, (pipelinePath, ))
        out = res.fetchone()
        if out is None:
            res = self._dbCur.execute(PIPELINES_ADD, (pipelinePath, ))
            pId = res.fetchone()[0]
            run = 1
        else:
            pId = out[0]
            run = out[1]
        self._dbCon.commit()
        return pId, run

    @lock
    def addRun(self, pipelineID: int, runNum: int, start: float,
               duration: float, status: PipelineStatus, maxRuns: int):
        values = {
            "pipeline_id": pipelineID,
            "run": runNum,
            "start_ts": int(start * 1000),
            "duration_ms": int(duration * 1000),
            "status": status.value
        }

        print("Adding run", values)

        self._dbCur.execute(RUNS_ADD, values)

        if maxRuns > 0:
            res = self._dbCur.execute(RUNS_GET_NUM_FOR_ID, (pipelineID, ))
            count = res.fetchone()[0]
            if count > maxRuns:
                values = {
                    "count": count - maxRuns,
                    "pipeline": pipelineID,
                }
                self._dbCur.execute(RUNS_DROP_OLDEST, values)

        self._dbCon.commit()

    @lock
    def getLastRun(
            self, pipelinePath: str
    ) -> tuple[int, float, float, PipelineStatus] | None:
        res = self._dbCur.execute(RUNS_GET_LAST_FOR_PIPELINE, (pipelinePath, ))
        x = res.fetchone()
        if x is None:
            return None

        return (
            int(x[0]),
            float(x[1] / 1000),
            float(x[2] / 1000),
            PipelineStatus(x[3]),
        )
