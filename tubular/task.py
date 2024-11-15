from typing import Dict, Any
import threading
import os
import uuid

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


class TaskDef:

    def __init__(self, repoPath: str, taskPath: str) -> None:
        self.repoPath = repoPath
        self.file = taskPath
        self.name = os.path.splitext(taskPath)[0]
        config = loadYAML(os.path.join(repoPath, self.file))

        try:
            self.display = config['meta']['display']
        except KeyError:
            self.display = self.name

        # whitelist tags
        self.whiteTags: set[str] = set()
        # blacklist tags
        self.blackTags: set[str] = set()

        try:
            nodeConfigs = config['node']
            try:
                # TODO error check
                self.whiteTags = set(nodeConfigs['requires'])
            except KeyError:
                pass
            try:
                self.blackTags = set(nodeConfigs['avoids'])
            except KeyError:
                pass
        except KeyError:
            pass

        self.steps: list[Step] = []

        stepConfigs = config['steps']
        for step in stepConfigs:
            self.steps.append(makeStep(step))


class Task:

    def __init__(self, repoUrl: str, branch: str, taskDef: TaskDef,
                 archivePath: str, outputPath: str) -> None:
        self.repoUrl = repoUrl
        self.branch = branch
        self.meta = taskDef
        self.status = PipelineStatus.NotRun
        self._statusNotify = threading.Condition()

        self.archiveZipFile = os.path.join(archivePath,
                                           f'{self.meta.name}.archive.zip')
        self.outputZipFile = os.path.join(outputPath,
                                          f'{self.meta.name}.output.zip')

    def setStatus(self, status: PipelineStatus):
        with self._statusNotify:
            self.status = status
            if self.status != PipelineStatus.Running:
                self._statusNotify.notify_all()

    def run(self, taskEnv: TaskEnv):
        self.status = PipelineStatus.Running
        with open(taskEnv.output, mode='w') as f:
            f.write(f"[ Run Task {self.meta.name} ]\n")
            for idx, step in enumerate(self.meta.steps):
                print(f"Running step {step.display}")
                taskEnv.taskStep = idx
                try:
                    step.run(taskEnv, f)
                except Exception as err:
                    print("Step failed:", err)
                    f.write(f'[ Task Failed ] {err}')
                    raise

            f.write(f'[ Task Complete ]')

    def waitForComplete(self) -> PipelineStatus:
        with self._statusNotify:
            while self.status == PipelineStatus.Running or self.status == PipelineStatus.NotRun:
                self._statusNotify.wait()
            return self.status

    def toTaskReq(self, args: dict[str, Any] = {}) -> TaskRequest:
        return TaskRequest(repo_url=self.repoUrl,
                           branch=self.branch,
                           task_path=self.meta.file,
                           args=args)
