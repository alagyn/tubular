import enum
import threading
from typing import Dict, Any
import os
from collections import deque

from tubular.config_loader import load_configs
from tubular.pipeline import Pipeline


class NodeStatus(enum.IntEnum):
    Idle = enum.auto()
    Active = enum.auto()


class NodeState:

    def __init__(self) -> None:
        self.workspaceDir = ""
        self.taskQueue: deque[Pipeline] = deque()

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
                pipeline = self.taskQueue.popleft()
            self.runTask(pipeline)

    def queueTask(self, repo: str, pipeline: str, args: Dict[str, Any]):
        with self.taskQueueCV:
            # TODO
            self.taskQueueCV.notify()

    def runTask(self, pipeline: Pipeline):
        # TODO check if repo exists
        # TODO pipeline repo branches?
        pass
