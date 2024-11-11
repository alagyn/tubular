import subprocess as sp
import os
import uuid
from typing import TextIO

# TODO error checking

WORKSPACE = ""


def initWorkspace(root: str):
    global WORKSPACE
    WORKSPACE = os.path.join(root, "git-temp")
    if not os.path.exists(WORKSPACE):
        os.makedirs(WORKSPACE, exist_ok=True)


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


def clone(url: str, branch: str, path: str, outputFile: TextIO | None):
    _runCmd(["git", "clone", url, f"--branch={branch}", "--depth=1", path],
            outputFile=outputFile)


def pull(path: str, branch: str, outputFile: TextIO | None):
    _runCmd(["git", "fetch", "--depth=1"], path, outputFile)
    _runCmd(["git", "reset", "--hard", f"origin/{branch}"], path, outputFile)

    # TODO make this optional?
    # _runCmd(["git", "clean", "-dfx"], path)


def cloneOrPull(url: str,
                branch: str,
                path: str,
                outputFile: TextIO | None = None):
    if not os.path.exists(path):
        clone(url, branch, path, outputFile)
    else:
        pull(path, branch, outputFile)


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
