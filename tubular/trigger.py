from typing import Any
import glob
import re
import os

import tubular.git_cmds as git
from tubular.repo import Repo
from tubular.pipeline import PipelineReq
from tubular.constantManager import ConstManager
from tubular.tempManager import TempManager
from tubular.yaml import getStr


class Trigger:

    def __init__(self, config: dict[str, Any]) -> None:
        self.piplines: list[PipelineReq] = []

        try:
            self.name = config["name"]
        except KeyError:
            raise RuntimeError("Trigger missing name [triggers.*.name]")

        try:
            pipelineConfigs = config["pipelines"]
        except KeyError:
            raise RuntimeError(
                "Trigger missing target pipelines [triggers.*.pipelines]")

        for p in pipelineConfigs:
            try:
                target = p["target"]
            except KeyError:
                raise RuntimeError(
                    "Triggered pipeline missing target [triggers.*.pipelines.target]"
                )

            try:
                argsDict: dict[str, str] = p["args"]
            except KeyError:
                argsDict: dict[str, str] = {}

            args: list[dict[str, str]] = []
            for key, val in argsDict.items():
                args.append({key: val})

            req = PipelineReq(branch="", pipeline_path=target, args=args)
            self.piplines.append(req)

    def check(self) -> bool:
        raise NotImplementedError()


class CommitTrigger(Trigger):

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        try:
            url = config["repo"]
            url = ConstManager.replace(url)
        except KeyError:
            raise RuntimeError("Commit trigger missing repo url")

        try:
            branch = config["branch"]
            branch = ConstManager.replace(branch)
        except KeyError:
            raise RuntimeError("Commit trigger missing branch")

        self.repo = Repo(url, branch, "")

        try:
            patterns = list(config["include"])
            # compile the globs into REs
            self.patterns: list[re.Pattern] = [
                re.compile(glob.translate(x)) for x in patterns
            ]
        except KeyError:
            self.patterns = []

        self.curCommit = git.getLatestRemoteCommit(self.repo)

    def check(self) -> bool:
        remoteCommit = git.getLatestRemoteCommit(self.repo)
        if self.curCommit != remoteCommit:
            # if we have no patterns, always execute when a commit is made
            if len(self.patterns) == 0:
                good = True
            else:
                good = False
                # get a temp dir, or reuse an already cloned one
                # this gets freed in the controller via the prefix
                path = TempManager.getTempDir(f"trigger_{self.repo.url}")
                self.repo.path = path
                if not os.path.exists(os.path.join(path, ".git")):
                    # clone empty repo since all we need is the commit log
                    git.cloneEmpty(self.repo)
                # else, use already cloned dir
                changedFiles = git.getChangedFiles(self.repo, self.curCommit,
                                                   remoteCommit)
                # check if any of the files match one of the patterns
                for pattern in self.patterns:
                    for file in changedFiles:
                        if pattern.fullmatch(file):
                            good = True
                            break
                    if good:
                        break

                self.repo.path = ""

            # update to the latest commit hash
            self.curCommit = remoteCommit
            return good
        # else, no change
        return False


class ScheduleTrigger(Trigger):

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        # TODO

    def check(self) -> bool:
        return super().check()


def makeTrigger(config: dict[str, Any]) -> Trigger:
    val = getStr(config, "type")
    match val:
        case "commit":
            return CommitTrigger(config)
        case "schedule":
            return ScheduleTrigger(config)
        case _:
            raise RuntimeError(f"Invalid trigger type: {val}")
