import enum


class PipelineStatus(enum.IntEnum):

    # Pipeline definition error
    Error = enum.auto()
    # Pipeline runtime error
    Fail = enum.auto()
    # Success
    Success = enum.auto()
