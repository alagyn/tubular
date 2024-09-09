import enum
from typing import Dict, Any
import subprocess as sp
import os
import sys

from tubular.task_env import TaskEnv, TaskOS


class StepType(enum.IntEnum):
    Clone = enum.auto()
    Shell = enum.auto()
    Exec = enum.auto()
    Archive = enum.auto()


def strToStepType(e: str) -> StepType:
    match e.lower():
        case 'clone':
            return StepType.Clone
        case 'shell':
            return StepType.Shell
        case 'exec':
            return StepType.Exec
        case 'archive':
            return StepType.Archive
        case _:
            raise RuntimeError(f"Invalid Step type string: {e}")


def getStr(config, key) -> str:
    val = config[key]
    if not isinstance(val, str):
        raise RuntimeError(
            f"Invalid entry for {key}, expected string got: {val}")
    return val


class Step:

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name = name
        try:
            val = getStr(config, 'display')
        except KeyError:
            self.display = self.name

    def run(self, taskEnv: TaskEnv):
        raise NotImplemented()


class _StepActionClone(Step):

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.repo = getStr(config, "repo")
        self.branch = getStr(config, "branch")

    def run(self, taskEnv: TaskEnv):
        sp.run(args=["git", "clone", self.branch, "-b", self.branch],
               cwd=taskEnv.workspace)


class _StepActionShell(Step):

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.lang = getStr(config, "lang")
        self.script = getStr(config, "script")

    def run(self, taskEnv: TaskEnv):
        args = []
        match self.lang.lower():
            case 'shell':
                args.append("sh")
                ext = 'sh'
            case 'batch' | 'bat':
                ext = 'bat'
            case 'powershell' | 'ps':
                ext = 'ps'
            case 'python' | 'py':
                args.append(sys.executable)
                ext = 'py'
            case _:
                # TODO move this check to the init?
                raise RuntimeError(f"Invalid script language: {self.lang}")

        scriptFile = os.path.join(taskEnv.workspace, f'{self.name}.{ext}')

        with open(scriptFile, mode="w") as f:
            f.write(self.script)

        args.append(scriptFile)

        sp.run(args=args, cwd=taskEnv.workspace)


class _StepActionExec(Step):

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.target = getStr(config, str)

    def run(self, taskEnv: TaskEnv):
        pass


class _StepActionArchive(Step):

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.target = getStr(config, str)

    def run(self, taskEnv: TaskEnv):
        pass


def makeStep(name: str, config: Dict[str, Any]) -> Step:
    try:
        val = getStr(config, "type")
        stepType = strToStepType(val)
    except KeyError:
        stepType = strToStepType(name)

    match stepType:
        case StepType.Clone:
            return _StepActionClone(name, config)
        case StepType.Shell:
            return _StepActionShell(name, config)
        case StepType.Exec:
            return _StepActionExec(name, config)
        case StepType.Archive:
            return _StepActionArchive(name, config)
