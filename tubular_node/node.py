import enum
import threading
from typing import Dict, Any
import os
from collections import deque

from pydantic import BaseModel

from tubular.config_loader import load_configs
from tubular.pipeline import Pipeline
from tubular import git_cmds
from tubular.task import Task
from tubular.yaml import loadYAML
from tubular.task_env import TaskEnv


class NodeStatus(enum.IntEnum):
    Idle = enum.auto()
    Active = enum.auto()


class TaskRequest(BaseModel):
    repo_url: str
    branch: str
    task_path: str
    args: Dict[str, str]

    def getRepoPath(self):
        return os.path.join(git_cmds.getRepoName(self.repo_url), self.branch)


# TODO clean up old pipeline repos/branches?


class NodeState:

    def __init__(self) -> None:
        self.workspaceDir = ""
        self.taskQueue: deque[TaskRequest] = deque()

        self.status = NodeStatus.Idle
        self.workerThread = threading.Thread()
        self.taskQueueCV = threading.Condition()
        self.shouldRun = True

    def start(self):
        config = load_configs()
        self.workspaceDir = config["node"]["workspace-root"]

        if not os.path.exists(self.workspaceDir):
            os.makedirs(self.workspaceDir, exist_ok=True)

        self.workerThread = threading.Thread(target=self.management_thread)
        self.workerThread.start()

    def stop(self):
        # TODO?
        with self.taskQueueCV:
            self.shouldRun = False
            self.taskQueueCV.notify()
        self.workerThread.join()

    def management_thread(self):
        while True:
            with self.taskQueueCV:
                if len(self.taskQueue) == 0:
                    self.taskQueueCV.wait()
                if not self.shouldRun:
                    break
                task = self.taskQueue.popleft()
            self.status = NodeStatus.Active
            self.runTask(task)
            self.status = NodeStatus.Idle

    def queueTask(self, task: TaskRequest):
        with self.taskQueueCV:
            self.taskQueue.append(task)
            self.taskQueueCV.notify()

    def runTask(self, taskReq: TaskRequest):
        repoDir = os.path.join(self.workspaceDir, taskReq.getRepoPath())
        if not os.path.exists(repoDir):
            print(f"Cloning task url: {taskReq.repo_url}")
            git_cmds.clone(taskReq.repo_url, taskReq.branch, repoDir)
        else:
            git_cmds.pull(repoDir)

        taskFile = os.path.join(repoDir, taskReq.task_path)
        taskConfig = loadYAML(taskFile)
        task = Task(taskReq.task_path, taskConfig)
        taskWorkspace = os.path.join(self.workspaceDir, taskReq.getRepoPath(),
                                     f'{taskReq.task_path}.workspace')

        if not os.path.isdir(taskWorkspace):
            os.makedirs(taskWorkspace, exist_ok=True)

        taskEnv = TaskEnv(taskWorkspace, taskReq.args)

        task.run(taskEnv)
        print("Task complete")
