import enum
import threading

import os

from yaml import load, dump
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class NodeStatus(enum.IntEnum):
    Idle = enum.auto()
    Active = enum.auto()


class NodeState:

    def __init__(self) -> None:
        self.workspaceDir = ""
        self.taskQueue = []
        self.status = NodeStatus.Idle

        self.workerThread = threading.Thread()
        self.taskQueueCV = threading.Condition()
        self.shouldRun = True

    def start(self):
        try:
            cfgFile = os.environ["TUBULAR_CONFIG"]
        except KeyError:
            cfgFile = "node.yaml"

        if not os.path.exists(cfgFile):
            raise RuntimeError(
                f"Cannot find config file: {cfgFile}, or TUBULAR_CONFIG variable not defined"
            )

        with open(cfgFile, mode='wb') as f:
            config = load(f, Loader)

        self.workspaceDir = config["node"]["workspace-root"]

        if not os.path.exists(self.workspaceDir):
            os.makedirs(self.workspaceDir, exist_ok=True)

        self.workerThread = threading.Thread(self.management_thread)
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

    def queueTask(self):
        with self.taskQueueCV:
            # TODO
            self.taskQueueCV.notify()
