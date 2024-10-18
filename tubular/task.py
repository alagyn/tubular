from typing import Dict, Any
import threading
import os

from pydantic import BaseModel

from tubular.step import makeStep, Step
from tubular.task_env import TaskEnv
from tubular.yaml import loadYAML
from tubular import git_cmds
from tubular.enums import PipelineStatus


class TaskRequest(BaseModel):
    repo_url: str
    branch: str
    task_path: str
    args: Dict[str, str]

    def getRepoPath(self):
        return os.path.join(git_cmds.getRepoName(self.repo_url), self.branch)


class Task:

    def __init__(self, req: TaskRequest, repoPath: str) -> None:

        self.file = req.task_path
        self.name = os.path.splitext(req.task_path)[0]
        config = loadYAML(os.path.join(repoPath, self.file))

        self.status = PipelineStatus.Running

        self._statusNotify = threading.Condition()

        try:
            self.display = config['meta']['display']
        except KeyError:
            self.display = self.name

        # whitelist tags
        self.whiteTags: set[str] = set()
        # blacklist tags
        self.blackTags: set[str] = set()

        try:
            nodeReq = config['node']
            try:
                # TODO error check
                self.whiteTags = set(nodeReq['requires'])
            except KeyError:
                pass
            try:
                self.blackTags = set(nodeReq['avoids'])
            except KeyError:
                pass
        except KeyError:
            pass

        self.steps: list[Step] = []

        stepConfigs = config['steps']
        for step in stepConfigs:
            self.steps.append(makeStep(step))

    def setStatus(self, status: PipelineStatus):
        with self._statusNotify:
            self.status = status
            if self.status != PipelineStatus.Running:
                self._statusNotify.notify_all()

    def run(self, taskEnv: TaskEnv):
        for idx, step in enumerate(self.steps):
            print(f"Running step {step.display}")
            taskEnv.taskStep = idx
            step.run(taskEnv)

    def waitForComplete(self) -> PipelineStatus:
        with self._statusNotify:
            while self.status == PipelineStatus.Running:
                self._statusNotify.wait()
            return self.status
