import enum
from typing import Dict, Any, TextIO
import subprocess as sp
import os
import sys
import shutil

from tubular import git_cmds
from tubular.task_env import TaskEnv
from tubular.file_utils import sanitizeFilepath


class StepType(enum.IntEnum):
    Clone = enum.auto()
    Script = enum.auto()
    Exec = enum.auto()
    Archive = enum.auto()
    # TODO GetArchive, copy paths from previous stages archives


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

    def run(self, taskEnv: TaskEnv, out: TextIO):
        raise NotImplementedError()


class _StepActionClone(Step):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.url = getStr(config, "url")
        self.branch = getStr(config, "branch")

    def run(self, taskEnv: TaskEnv, out: TextIO):
        url = taskEnv.replace(self.url)
        branch = taskEnv.replace(self.branch)

        path = os.path.join(taskEnv.workspace, git_cmds.getRepoName(url))

        out.write(f"[ Clone {url} {branch}] ({taskEnv.getTime()})\n")
        out.flush()
        git_cmds.cloneOrPull(url, branch, path, out)


class _StepActionScript(Step):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.lang = getStr(config, "lang")
        self.script = getStr(config, "script")

    def run(self, taskEnv: TaskEnv, out: TextIO):
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

        out.write(f"[ Script {scriptFile} ] ({taskEnv.getTime()})\n")
        out.flush()
        ret = sp.call(args=args,
                      cwd=taskEnv.workspace,
                      stdout=out,
                      stderr=sp.STDOUT)
        if ret != 0:
            # TODO
            out.write(f"[ Script Failed, Code={ret}] ({taskEnv.getTime()})\n")
            out.flush()
            raise RuntimeError("Script failed")


class _StepActionExec(Step):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.target = getStr(config, "target")

    def run(self, taskEnv: TaskEnv, out: TextIO):
        target = taskEnv.replace(self.target)
        out.write(f"[ Exec {target}] ({taskEnv.getTime()})\n")
        out.flush()
        ret = sp.run(args=target.split(),
                     cwd=taskEnv.workspace,
                     stdout=out,
                     stderr=sp.STDOUT)
        if ret.returncode != 0:
            # TODO
            raise RuntimeError(f"Exec returned {ret.returncode}")


class _StepActionArchive(Step):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.target = getStr(config, "target")

    def run(self, taskEnv: TaskEnv, out: TextIO):
        out.write(f'[ Archive {self.target} ] ({taskEnv.getTime()})\n')
        target = taskEnv.replace(self.target)
        fullpath = sanitizeFilepath(taskEnv.workspace, target)
        if not os.path.exists(fullpath):
            msg = f"Target '{fullpath}' does not exist"
            out.write(msg)
            out.write("\n")
            raise RuntimeError(msg)

        outpath = os.path.relpath(fullpath, taskEnv.workspace)
        outpath = os.path.join(taskEnv.archive, outpath)

        # TODO just make the target be a glob?
        # could make this conditional not needed
        # and we could log each file

        if os.path.isdir(fullpath):
            out.write(f"Archiving directory: {fullpath}\n")
            shutil.copytree(fullpath,
                            outpath,
                            symlinks=True,
                            dirs_exist_ok=True)
        else:
            out.write(f"Archiving file: {fullpath}\n")
            shutil.copy(fullpath, outpath)
        out.flush()


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
