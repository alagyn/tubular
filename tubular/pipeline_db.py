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
    (:path, 0)
RETURNING
    id
"""

PIPELINES_GET_ID = """
SELECT
    id
FROM
    pipelines
WHERE
    path = ?
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
    branch TEXT,
    run INTEGER,
    start_ts INTEGER,
    duration_ms INTEGER,
    status INTEGER,
    FOREIGN KEY(pipeline) REFERENCES pipelines(id)
)
"""

RUNS_ADD = """
INSERT INTO runs
    (pipeline, branch, run, start_ts, duration_ms, status)
VALUES
    (:pipeline_id, :branch, :run, :start_ts, 0, 2)
"""

RUNS_SET_DATA = """
UPDATE
    runs
SET
    duration_ms = :duration_ms,
    status = :status
WHERE
    pipeline = :pipeline_id
    AND
    run = :run
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
    branch, run, start_ts, duration_ms, status
FROM
    runs
WHERE
    pipeline = ?
ORDER BY
    runs.run DESC
LIMIT 1
"""

RUNS_GET_FOR_PIPELINE = """
SELECT
    branch, run, start_ts, duration_ms, status
FROM
    runs
WHERE
    pipeline = ?
ORDER BY
    runs.run DESC
"""

RUNS_GET_LAST_50_STATUS = """
SELECT
    status
FROM
    runs
ORDER BY
    run DESC
LIMIT 50
"""

RUNS_SET_RUNNING_ERROR = """
UPDATE
    runs
SET
    status = 0
WHERE
    status = 2
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


class Run:

    def __init__(self, pipelineId: int, branch: str, runNum: int,
                 startTime: float, duration: float, status: int) -> None:
        self.pipelineId = pipelineId
        self.branch = branch
        self.runNum = runNum
        self.startTime = startTime
        self.duration = duration
        self.status = PipelineStatus(status)


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
        else:
            # Make any running pipelines set to error
            self._dbCur.execute(RUNS_SET_RUNNING_ERROR)
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
    def addRun(self, pipelineID: int, runNum: int, branch: str, start: float,
               maxRuns: int):
        values = {
            "pipeline_id": pipelineID,
            "branch": branch,
            "run": runNum,
            "start_ts": int(start * 1000),
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
    def setRunStatus(self, pipelineID: int, runNum: int, duration: float,
                     status: PipelineStatus):
        values = {
            "pipeline_id": pipelineID,
            "run": runNum,
            "duration_ms": int(duration * 1000),
            "status": status.value
        }

        self._dbCur.execute(RUNS_SET_DATA, values)
        self._dbCon.commit()

    @lock
    def getPipelineId(self, pipelinePath: str) -> int:
        ret = self._dbCur.execute(PIPELINES_GET_ID, (pipelinePath, ))
        val = ret.fetchone()
        if val is None:
            res = self._dbCur.execute(PIPELINES_ADD, (pipelinePath, ))
            pId = res.fetchone()[0]
        else:
            pId = val[0]

        return pId

    @lock
    def getLastRun(self, pipelineId: int) -> Run | None:
        res = self._dbCur.execute(RUNS_GET_LAST_FOR_PIPELINE, (pipelineId, ))
        x = res.fetchone()
        if x is None:
            return None

        return Run(
            pipelineId,
            str(x[0]),
            int(x[1]),
            float(x[2] / 1000),
            float(x[3] / 1000),
            x[4],
        )

    @lock
    def getRuns(self, pipelineId: int) -> list[Run]:
        res = self._dbCur.execute(RUNS_GET_FOR_PIPELINE, (pipelineId, ))
        out = []
        for x in res.fetchall():
            out.append(
                Run(
                    pipelineId,
                    str(x[0]),
                    int(x[1]),
                    float(x[2] / 1000),
                    float(x[3] / 1000),
                    x[4],
                ))

        return out

    @lock
    def getLast50RunsStatus(self) -> list[PipelineStatus]:
        res = self._dbCur.execute(RUNS_GET_LAST_50_STATUS)
        out = [PipelineStatus(x[0]) for x in res.fetchall()]
        return out
