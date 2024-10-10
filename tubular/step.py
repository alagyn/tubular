import enum
from typing import Dict, Any
import subprocess as sp
import os
import sys
import shutil

from tubular import git_cmds
from tubular.task_env import TaskEnv


class StepType(enum.IntEnum):
    Clone = enum.auto()
    Script = enum.auto()
    Exec = enum.auto()
    Archive = enum.auto()


def strToStepType(e: str) -> StepType:
    match e.lower():
        case 'clone':
            return StepType.Clone
        case 'script':
            return StepType.Script
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


# TODO capture output


class Step:

    def __init__(self, config: Dict[str, Any]) -> None:
        try:
            val = getStr(config, 'display')
            self.display = val
        except KeyError:
            self.display = getStr(config, "type")

    def run(self, taskEnv: TaskEnv):
        raise NotImplementedError()


class _StepActionClone(Step):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.url = getStr(config, "url")
        self.branch = getStr(config, "branch")

    def run(self, taskEnv: TaskEnv):
        url = taskEnv.replace(self.url)
        branch = taskEnv.replace(self.branch)

        path = os.path.join(taskEnv.workspace, git_cmds.getRepoName(url))

        if not os.path.exists(path):
            print(f"Cloning {url}:{branch} into {path}")
            git_cmds.clone(url, branch, path)
        else:
            print(f"Pulling {url}:{branch} into {path}")
            git_cmds.pull(path)


class _StepActionScript(Step):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
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

        scriptName = f'step-{taskEnv.taskStep}.{ext}'
        scriptFile = os.path.join(taskEnv.workspace, scriptName)

        with open(scriptFile, mode="w") as f:
            text = taskEnv.replace(self.script)
            f.write(text)

        args.append(scriptName)

        ret = sp.call(args=args, cwd=taskEnv.workspace)
        if ret != 0:
            # TODO
            raise RuntimeError("Script failed")


class _StepActionExec(Step):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.target = getStr(config, "target")

    def run(self, taskEnv: TaskEnv):
        target = taskEnv.replace(self.target)
        sp.run(args=target.split(), cwd=taskEnv.workspace)


class _StepActionArchive(Step):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.target = getStr(config, "target")

    def run(self, taskEnv: TaskEnv):
        target = taskEnv.replace(self.target)
        if not os.path.exists(target):
            raise RuntimeError("target does not exist")
        if not os.path.exists(taskEnv.archive):
            os.makedirs(taskEnv.archive, exist_ok=True)
        if os.path.isdir(target):
            shutil.copytree(target,
                            taskEnv.archive,
                            symlinks=True,
                            dirs_exist_ok=True)
        else:
            shutil.copy(target, taskEnv.archive)


def makeStep(config: Dict[str, Any]) -> Step:
    val = getStr(config, "type")
    stepType = strToStepType(val)

    match stepType:
        case StepType.Clone:
            return _StepActionClone(config)
        case StepType.Script:
            return _StepActionScript(config)
        case StepType.Exec:
            return _StepActionExec(config)
        case StepType.Archive:
            return _StepActionArchive(config)
