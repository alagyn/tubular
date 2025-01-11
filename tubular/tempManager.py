from contextlib import contextmanager
from uuid import uuid4
import os
import shutil
from typing import Generator


class TempManager:
    _workspace = ""
    # id -> dir
    _tempDirs: dict[str, str] = {}

    def __init__(self) -> None:
        raise NotImplementedError()

    @classmethod
    def setWorkspace(cls, workspace: str):
        # clear the workspace
        if os.path.isdir(workspace):
            shutil.rmtree(workspace)

        os.makedirs(workspace, exist_ok=True)
        cls._workspace = workspace

    @classmethod
    def getTempDir(cls, tempID: str) -> str:
        """
        Get a new random tempdir, or an existing on if the ID is in use
        """
        try:
            return cls._tempDirs[tempID]
        except KeyError:
            tempdir = os.path.join(cls._workspace, uuid4().hex)
            os.makedirs(tempdir)
            cls._tempDirs[tempID] = tempdir
        return tempdir

    @classmethod
    def freeTempDir(cls, tempID: str):
        """
        Delete a tempdir
        """
        tempdir = cls._tempDirs.pop(tempID)
        shutil.rmtree(tempdir)

    @classmethod
    def freeTempDirsByPrefix(cls, prefix: str):
        keys = list(cls._tempDirs.keys())
        for key in keys:
            if key.startswith(prefix):
                cls.freeTempDir(key)


@contextmanager
def tempdir() -> Generator[str, None, None]:
    """
    Context manager that creates a temp directory in the workspace
    and deletes the contents after the manager exits
    """
    tid = uuid4().hex
    t = TempManager.getTempDir(tid)
    try:
        yield t
    finally:
        TempManager.freeTempDir(tid)
