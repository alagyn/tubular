import os
import enum


class TaskOS(enum.IntEnum):
    Win = enum.auto()
    Linux = enum.auto()


class TaskEnv:
    """
    Various configs for the current task
    """

    def __init__(self, workspace: str) -> None:
        # TODO
        self.workspace = workspace
        self.archive = os.path.join(workspace, "archive")
        self.os = TaskOS.Linux
