from typing import Dict, Any
import os

from pydantic import BaseModel

from tubular.stage import Stage
from tubular import git_cmds
from tubular.yaml import loadYAML


class PipelineReq(BaseModel):
    repo_url: str
    branch: str
    pipeline_path: str
    args: Dict[str, str]

    def getRepoPath(self):
        return os.path.join(git_cmds.getRepoName(self.repo_url), self.branch)


class Pipeline:

    def __init__(self, req: PipelineReq, repoPath: str) -> None:

        self.file = req.pipeline_path
        self.name = os.path.splitext(req.pipeline_path)[0]
        config = loadYAML(os.path.join(repoPath, self.file))

        self.repo_url = req.repo_url
        self.branch = req.branch
        self.path = req.pipeline_path
        self.args = {}
        try:
            self.args.update(config["args"])
        except KeyError:
            pass
        # Overwrite defaults with user supplied
        self.args.update(req.args)

        try:
            self.display = config['meta']['display']
        except KeyError:
            self.display = self.name

        self.stages: list[Stage] = []
        for stageConfig in config['stages']:
            self.stages.append(
                Stage(self.repo_url, self.branch, repoPath, stageConfig,
                      self.args))

    def run(self):
        pass
