import enum
import threading
from typing import Dict, Any
import os

from collections import deque

from tubular.config_loader import load_configs
from tubular.pipeline import Pipeline
from tubular import git_cmds
from tubular.task import Task, TaskRequest

from tubular.task_env import TaskEnv


class NodeStatus(enum.IntEnum):
    Offline = enum.auto()
    Idle = enum.auto()
    Active = enum.auto()


# TODO clean up old pipeline repos/branches?


class NodeState:

    def __init__(self) -> None:
        self.workspace = ""
        self.taskQueue: deque[TaskRequest] = deque()

        self.status = NodeStatus.Idle
        self.workerThread = threading.Thread()
        self.taskQueueCV = threading.Condition()
        self.shouldRun = True

    def start(self):
        config = load_configs()
        self.workspace = config["node"]["workspace-root"]

        if not os.path.exists(self.workspace):
            os.makedirs(self.workspace, exist_ok=True)

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
        repoDir = os.path.join(self.workspace, taskReq.getRepoPath())
        git_cmds.cloneOrPull(taskReq.repo_url, taskReq.branch, repoDir)

        task = Task(taskReq, repoDir)

        taskDir = os.path.join(self.workspace, taskReq.getRepoPath())
        taskWorkspace = os.path.join(taskDir, f'{task.name}.workspace')
        taskArchive = os.path.join(taskDir, f'{task.name}.archive')

        if not os.path.isdir(taskWorkspace):
            os.makedirs(taskWorkspace, exist_ok=True)
        if not os.path.isdir(taskArchive):
            os.makedirs(taskArchive, exist_ok=True)

        taskEnv = TaskEnv(taskWorkspace, taskArchive, taskReq.args)

        task.run(taskEnv)
        print("Task complete")
