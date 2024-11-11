import enum


class PipelineStatus(enum.IntEnum):

    # Pipeline definition error
    Error = 0
    # Pipeline runtime error
    Fail = 1
    # In progress
    Running = 2
    # Success
    Success = 3
    # Queued
    Queued = 4


class NodeStatus(enum.IntEnum):
    Offline = enum.auto()
    Idle = enum.auto()
    Active = enum.auto()
    Archiving = enum.auto()
