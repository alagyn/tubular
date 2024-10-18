from typing import Dict, Any
import os

from pydantic import BaseModel

from tubular.stage import Stage
from tubular import git_cmds
from tubular.yaml import loadYAML
from tubular import pipeline_db
from tubular.enums import PipelineStatus


class PipelineReq(BaseModel):
    branch: str
    pipeline_path: str
    args: Dict[str, str]


class Pipeline:

    def __init__(self, repoUrl: str, req: PipelineReq, repoPath: str) -> None:

        self.file = req.pipeline_path
        self.name = os.path.splitext(req.pipeline_path)[0]
        config = loadYAML(os.path.join(repoPath, self.file))

        self.status = PipelineStatus.Running

        self.branch = req.branch
        self.path = req.pipeline_path
        self.archive = os.path.join(repoPath, f'{self.name}.archive')

        if not os.path.exists(self.archive):
            os.makedirs(self.archive, exist_ok=True)

        dbfile = os.path.join(self.archive, 'pipeline.db')

        self._db = pipeline_db.inst.getDB(dbfile)

        self.args = {}
        try:
            self.args.update(config["args"])
        except KeyError:
            pass
        # Overwrite defaults with user supplied
        self.args.update(req.args)

        try:
            meta = config['meta']
            self.display = str(meta.get('display', self.name))
            self.maxRuns = int(meta.get('keep-runs', 0))
        except KeyError:
            self.display = self.name
            self.maxRuns = 0

        # TODO catch errors? set status to Error

        self.stages: list[Stage] = []
        for stageConfig in config['stages']:
            self.stages.append(
                Stage(repoUrl, self.branch, repoPath, stageConfig, self.args))

    def save(self, startTime: float, endTime: float):
        runNum = self._db.getNextRunNum()
        self._db.addRun(runNum, startTime, endTime - startTime, self.status,
                        self.maxRuns)
