import enum
import threading
from typing import Dict, Any
import os

from collections import deque

from tubular.config_loader import load_configs
from tubular.pipeline import Pipeline
from tubular import git_cmds
from tubular.task import Task, TaskRequest
from tubular.enums import NodeStatus, PipelineStatus
from tubular.task_env import TaskEnv

# TODO clean up old pipeline repos/branches?


class NodeState:

    def __init__(self) -> None:
        self.workspace = ""
        self.status = NodeStatus.Idle
        self.workerThread = threading.Thread()
        self.taskStatus = PipelineStatus.Success

    def start(self):
        config = load_configs()
        self.workspace = config["node"]["workspace-root"]
        git_cmds.initWorkspace(self.workspace)

        if not os.path.exists(self.workspace):
            os.makedirs(self.workspace, exist_ok=True)

    def stop(self):
        if self.workerThread.is_alive():
            self.workerThread.join()

    def queueTask(self, task: TaskRequest):
        if self.status == NodeStatus.Active:
            raise RuntimeError("Task already running")

        self.taskStatus = PipelineStatus.Running

        self.status = NodeStatus.Active
        self.workerThread = threading.Thread(
            target=self.runTask,
            args=(task, ),
        )
        self.workerThread.start()

    def runTask(self, taskReq: TaskRequest):
        try:
            repoDir = os.path.join(self.workspace, taskReq.getRepoPath())
            git_cmds.cloneOrPull(taskReq.repo_url, taskReq.branch, repoDir)
            task = Task(taskReq, repoDir)
        except:
            self.taskStatus = PipelineStatus.Error
            raise

        taskDir = os.path.join(self.workspace, taskReq.getRepoPath())
        taskWorkspace = os.path.join(taskDir, f'{task.name}.workspace')
        taskArchive = os.path.join(taskDir, f'{task.name}.archive')

        if not os.path.isdir(taskWorkspace):
            os.makedirs(taskWorkspace, exist_ok=True)
        if not os.path.isdir(taskArchive):
            os.makedirs(taskArchive, exist_ok=True)

        taskEnv = TaskEnv(taskWorkspace, taskArchive, taskReq.args)

        try:
            task.run(taskEnv)
            self.taskStatus = PipelineStatus.Success
        except:
            self.taskStatus = PipelineStatus.Fail
        print("Task complete")
        self.status = NodeStatus.Idle
