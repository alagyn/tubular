import subprocess as sp
import os

# TODO error checking


def clone(url: str, branch: str, path: str):
    sp.run(args=["git", "clone", url, f"--branch={branch}", "--depth=1", path])


def pull(path: str, branch: str):
    sp.run(args=["git", "fetch", "--depth=1"], cwd=path)
    sp.run(args=["git", "reset", "--hard", f"origin/{branch}"], cwd=path)
    # TODO make this optional?
    sp.run(args=["git", "clean", "-dfx"], cwd=path)


def cloneOrPull(url: str, branch: str, path: str):
    if not os.path.exists(path):
        clone(url, branch, path)
    else:
        pull(path, branch)


def getRepoName(url: str) -> str:
    stripped = url.strip("/")
    if stripped.endswith(".git"):
        stripped = stripped[:-4]
    return stripped.split("/")[-1]
