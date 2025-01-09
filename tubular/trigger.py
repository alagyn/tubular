from typing import Any
import glob
import re
import os
import datetime
import re

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
                if not isinstance(target, str):
                    raise RuntimeError("Invalid trigger pipeline target")
            except KeyError:
                raise RuntimeError(
                    "Triggered pipeline missing target [triggers.*.pipelines.target]"
                )

            try:
                argsDict: dict[str, str] = p["args"]
            except KeyError:
                argsDict: dict[str, str] = {}

            if not target.endswith(".yaml"):
                target = f'{target}.yaml'

            args: list[dict[str, str]] = []
            for key, val in argsDict.items():
                args.append({"k": key, "v": val})

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


_TIME_RE = re.compile(
    r"(?P<day>\w+)? *(?P<hour>\d{1,2})(:(?P<min>\d{2}))?(?P<when>[aApP][mM])")

# Mon = 0, Sun = 6
_DAY_MAP = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thur": 3,
    "thu": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6
}


class ScheduleTrigger(Trigger):

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.nextRun = datetime.datetime.now()

        try:
            temp = config["period"]
            if not isinstance(temp, str):
                raise RuntimeError("Schedule trigger: Invalid period")
            num, unit = temp.strip().split()
        except KeyError:
            raise RuntimeError(
                "Schedule trigger missing period [triggers.*.period]")

        try:
            num = int(num)
        except:
            raise RuntimeError("Schedule trigger period: Invalid amount")

        self.offset = datetime.timedelta(days=1)

        if unit == "min":
            self.offset = datetime.timedelta(minutes=num)
            self.nextRun += self.offset
        elif unit == "hour":
            self.offset = datetime.timedelta(hours=num)
            self.nextRun += self.offset
        elif unit in ("day", "week"):
            try:
                when = config["when"]
                if not isinstance(when, str):
                    raise RuntimeError("Schedule trigger: invalid when value")
            except KeyError:
                raise RuntimeError(
                    f"Schedule trigger missing with unit {unit} missing when [triggers.*.when]"
                )

            whenMatch = _TIME_RE.fullmatch(when.strip())
            if whenMatch is None:
                raise RuntimeError(
                    f"Schedule trigger: Invalid when value '{when}'")

            whenMinVal = whenMatch.group("min")
            if whenMinVal is None:
                whenMin = 0
            else:
                whenMin = int(whenMinVal)

            if not 0 <= whenMin <= 59:
                raise RuntimeError(f"Schedule trigger: Invalid min {whenMin}")

            whenHour = int(whenMatch.group("hour"))
            if not 1 <= whenHour <= 12:
                raise RuntimeError(
                    f"Schedule trigger: Invalid hour {whenHour}")
            if whenMatch.group("when") == "pm":
                whenHour += 12
            # handle midnight
            elif whenHour == 12:
                whenHour = 0

            if unit == "day":
                self.offset = datetime.timedelta(days=num)

                # Figure out if we can run it today
                if self.nextRun.hour < whenHour or (
                        self.nextRun.hour == whenHour
                        and self.nextRun.minute < whenMin):
                    self.nextRun = datetime.datetime(self.nextRun.year,
                                                     self.nextRun.month,
                                                     self.nextRun.day,
                                                     whenHour, whenMin, 0)
                # else start tomorrow
                else:
                    temp = self.nextRun + datetime.timedelta(days=1)
                    self.nextRun = datetime.datetime(temp.year, temp.month,
                                                     temp.day, whenHour,
                                                     whenMin, 0)

            if unit == "week":
                self.offset = datetime.timedelta(weeks=num)

                whenDay = whenMatch.group("day")
                if whenDay is None:
                    raise RuntimeError(
                        "Schedule trigger: Weekly period missing day of week in 'when'"
                    )

                try:
                    whenDayNum = _DAY_MAP[whenDay.lower()]
                except KeyError:
                    raise RuntimeError(
                        f"Schedule trigger: Invalid day of week '{whenDay}'")

                curWeekDay = self.nextRun.weekday()

                # figure out if we can run it today
                if curWeekDay == whenDayNum:
                    if self.nextRun.hour < whenHour or (
                            self.nextRun.hour == whenHour
                            and self.nextRun.minute < whenMin):
                        self.nextRun = datetime.datetime(
                            self.nextRun.year, self.nextRun.month,
                            self.nextRun.day, whenHour, whenMin, 0)
                # else the next possible day
                else:
                    if curWeekDay < whenDayNum:
                        daysToWait = whenDayNum - curWeekDay
                    else:
                        # wait till the end of the current week, then the next day
                        daysToWait = (7 - curWeekDay) + whenDayNum
                    temp = self.nextRun + datetime.timedelta(days=daysToWait)
                    self.nextRun = datetime.datetime(temp.year, temp.month,
                                                     temp.day, whenHour,
                                                     whenMin, 0)

        else:
            raise RuntimeError(
                f"Schedule trigger: invalid period unit '{unit}'")

    def check(self) -> bool:
        if datetime.datetime.now() >= self.nextRun:
            self.nextRun += self.offset
            return True
        return False


def makeTrigger(config: dict[str, Any]) -> Trigger:
    val = getStr(config, "type")
    match val:
        case "commit":
            return CommitTrigger(config)
        case "schedule":
            return ScheduleTrigger(config)
        case _:
            raise RuntimeError(f"Invalid trigger type: {val}")
