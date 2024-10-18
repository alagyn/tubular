import enum


class PipelineStatus(enum.IntEnum):

    # Pipeline definition error
    Error = enum.auto()
    # Pipeline runtime error
    Fail = enum.auto()
    # In progress
    Running = enum.auto()
    # Success
    Success = enum.auto()


class NodeStatus(enum.IntEnum):
    Offline = enum.auto()
    Idle = enum.auto()
    Active = enum.auto()
