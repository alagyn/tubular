from typing import Dict, Any
import os

from pydantic import BaseModel

from tubular.stage import StageDef, Stage
from tubular import git_cmds
from tubular.yaml import loadYAML
from tubular import pipeline_db
from tubular.enums import PipelineStatus


class PipelineReq(BaseModel):
    branch: str
    pipeline_path: str
    args: list[dict[str, str]]


class PipelineDef:

    def __init__(self, repoPath: str, file: str) -> None:
        self.file = file
        self.name = os.path.splitext(self.file)[0]
        config = loadYAML(os.path.join(repoPath, self.file))

        try:
            args: dict[str, Any] = config["args"]
            self.args: list[tuple[str, str]] = [(key, str(val))
                                                for (key, val) in args.items()]
        except KeyError:
            self.args = []

        try:
            meta = config['meta']
            self.display = str(meta.get('display', self.name))
            self.maxRuns = int(meta.get('keep-runs', 0))
        except KeyError:
            self.display = self.name
            self.maxRuns = 0

        self.stages: list[StageDef] = []
        for stageConfig in config['stages']:
            self.stages.append(StageDef(repoPath, stageConfig))


class Pipeline:

    def __init__(self, pipelineDef: PipelineDef, req: PipelineReq,
                 repoPath: str) -> None:
        self.meta = pipelineDef
        self.status = PipelineStatus.Running

        self.branch = req.branch
        self.archive = os.path.join(repoPath, f'{self.meta.name}.archive')

        if not os.path.exists(self.archive):
            os.makedirs(self.archive, exist_ok=True)

        self.args = {key: val for key, val in self.meta.args}
        # Overwrite defaults with user supplied
        for kvPair in req.args:
            self.args[kvPair["k"]] = kvPair["v"]

        # TODO catch errors? set status to Error

        self.stages: list[Stage] = [Stage(x) for x in self.meta.stages]
