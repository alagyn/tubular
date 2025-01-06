import os
from typing import Dict
import time

from tubular.constantManager import ConstManager


class TaskEnv:
    """
    Various configs for the current task
    """

    def __init__(self, workspace: str, archive: str, output: str,
                 args: Dict[str, str]) -> None:
        # TODO
        self.workspace = workspace
        self.archive = archive
        self.output = output
        self.args: Dict[str, str] = args
        args["workspace"] = os.path.abspath(workspace)
        self.taskStep = 0
        self.startTime = 0.0

    def replace(self, text: str) -> str:
        return ConstManager.replace(text, self.args)

    def start(self):
        self.startTime = time.time()

    def getTime(self) -> str:
        diff = time.time() - self.startTime
        if diff < 1:
            return f'T+ {diff * 1000:.2f}ms'
        if diff < 60:
            return f'T+ {diff:.2f}s'

        numSecs = int(diff)
        mins = numSecs // 60
        secs = numSecs % 60

        if diff < 3600:
            return f'T+ {mins}min {secs}s'

        hrs = mins // 60

        return f'T+ {hrs}hr {mins}min {secs}s'
