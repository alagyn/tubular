from typing import Any

import tubular.git_cmds as git
from tubular.repo import Repo
from tubular.pipeline import Pipeline
from tubular.pipeline import PipelineReq
from tubular.constantManager import ConstManager


class Trigger:

    def __init__(self, config: dict[str, Any]) -> None:
        self.piplines: list[PipelineReq] = []

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

            req = PipelineReq(branch="", pipeline_path=p["target"], args=args)
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
        self.curCommit = git.getLatestRemoteCommit(self.repo)

    def check(self) -> bool:
        remoteCommit = git.getLatestRemoteCommit(self.repo)
        if self.curCommit != remoteCommit:
            self.curCommit = remoteCommit
            return True
        return super().check()


class ScheduleTrigger(Trigger):

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        # TODO

    def check(self) -> bool:
        return super().check()
