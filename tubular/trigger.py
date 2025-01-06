import tubular.git_cmds as git
from tubular.repo import Repo


class Trigger:

    def check(self) -> bool:
        raise NotImplementedError()


class CommitTrigger(Trigger):

    def __init__(self, repo: Repo) -> None:
        self.repo = repo
        self.curCommit = git.getCurrentLocalCommit(self.repo)

    def check(self) -> bool:
        remoteCommit = git.getLatestRemoteCommit(self.repo)
        if self.curCommit != remoteCommit:
            self.curCommit = remoteCommit
            return True
        return super().check()


class ScheduleTrigger(Trigger):

    def __init__(self) -> None:
        pass

    def check(self) -> bool:
        return super().check()
