import subprocess as sp
import os
import uuid
from typing import TextIO

from tubular.repo import Repo

# TODO error checking


def _runCmd(args, cwd=None, outputFile: TextIO | None = None):
    stdout = sp.DEVNULL if outputFile is None else outputFile
    ret = sp.run(args=args, cwd=cwd, stdout=stdout, stderr=sp.STDOUT)
    if ret.returncode != 0:
        raise RuntimeError(
            f'Error running git command, {cwd=}: {" ".join(args)}')


def _captureCmd(args, cwd=None) -> str:
    ret = sp.run(args=args, cwd=cwd, stdout=sp.PIPE, stderr=sp.STDOUT)
    if ret.returncode != 0:
        raise RuntimeError(
            f"Error running git command, {cwd=}: {' '.join(args)}\n{ret.stdout}"
        )
    return ret.stdout.decode()


def clone(repo: Repo, outputFile: TextIO | None):
    _runCmd([
        "git", "clone", repo.url, f"--branch={repo.branch}", "--depth=1",
        repo.path
    ],
            outputFile=outputFile)


def cloneEmpty(repo: Repo):
    _runCmd([
        "git", "clone", repo.url, "--sparse", "--filter=blob:none",
        "--no-checkout", repo.path
    ])


def pull(repo: Repo, outputFile: TextIO | None):
    _runCmd(["git", "fetch", "--depth=1"], repo.path, outputFile)
    _runCmd(["git", "reset", "--hard", f"origin/{repo.branch}"], repo.path,
            outputFile)

    # TODO make this optional?
    # _runCmd(["git", "clean", "-dfx"], path)


def cloneOrPull(repo: Repo, outputFile: TextIO | None = None):
    if not os.path.exists(repo.path):
        clone(repo, outputFile)
    else:
        pull(repo, outputFile)


def getRepoName(url: str) -> str:
    stripped = url.strip("/")
    if stripped.endswith(".git"):
        stripped = stripped[:-4]
    return stripped.split("/")[-1]


def getBranches(url: str) -> list[str]:
    output = _captureCmd(["git", "ls-remote", "-b", url])
    out = []
    for line in output.splitlines():
        branch = line.split("\t")[1]
        if branch.startswith("refs/heads/"):
            branch = branch[11:]
        out.append(branch)
    return out


def getCurrentLocalCommit(repo: Repo) -> bytearray:
    output = _captureCmd(["git", "rev-parse", "HEAD"], repo.path)
    return bytearray.fromhex(output.strip())


def getLatestRemoteCommit(repo: Repo) -> bytearray:
    output = _captureCmd(["git", "ls-remote", "-b", repo.url, repo.branch])
    commitHashStr = output.split()[0]
    return bytearray.fromhex(commitHashStr)


def getLatestRemoteCommits(repo: Repo) -> dict[str, bytearray]:
    output = _captureCmd(["git", "ls-remote", "-b", repo.url])
    out = {}
    for line in output.splitlines():
        commitHashStr, branch = line.split()
        if branch.startswith("refs/heads/"):
            branch = branch[11:]
        out[branch] = bytearray.fromhex(commitHashStr)
    return out


def getChangedFiles(repo: Repo, commit1: bytes, commit2: bytes) -> list[str]:
    output = _captureCmd(
        ["git", "diff", "--name-only", f'{commit1.hex()}..{commit2.hex()}'],
        cwd=repo.path)

    return output.splitlines()
