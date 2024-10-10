import os
from typing import Dict, List
import re

_REPL_RE = re.compile(r"@\{(?P<arg>\w+)\}")


class TaskEnv:
    """
    Various configs for the current task
    """

    def __init__(self, workspace: str, archive: str, args: Dict[str,
                                                                str]) -> None:
        # TODO
        self.workspace = workspace
        self.archive = archive
        self.args: Dict[str, str] = args
        args["workspace"] = os.path.abspath(workspace)
        self.taskStep = 0

    def replace(self, text: str) -> str:

        def _repl(key: re.Match) -> str:
            try:
                return self.args[key.group("arg")]
            except KeyError:
                return key.group()

        return _REPL_RE.sub(_repl, text)
