import subprocess as sp
import os
import uuid

# TODO error checking

WORKSPACE = ""


def initWorkspace(root: str):
    global WORKSPACE
    WORKSPACE = os.path.join(root, "git-temp")
    if not os.path.exists(WORKSPACE):
        os.makedirs(WORKSPACE, exist_ok=True)


def _runCmd(args, cwd=None):
    tempFile = os.path.join(WORKSPACE, f'{uuid.uuid4()}.log')
    with open(tempFile, mode='w') as f:
        ret = sp.run(args=args, cwd=cwd, stdout=f, stderr=sp.STDOUT)
    if ret.returncode != 0:
        with open(tempFile, mode='r') as f:
            logs = f.read()
        os.remove(tempFile)
        raise RuntimeError(
            f'Error running git command, {cwd=}: {" ".join(args)}\n{logs}')
    os.remove(tempFile)


def clone(url: str, branch: str, path: str):
    _runCmd(["git", "clone", url, f"--branch={branch}", "--depth=1", path])


def pull(path: str, branch: str):
    _runCmd(["git", "fetch", "--depth=1"], path)
    _runCmd(["git", "reset", "--hard", f"origin/{branch}"], path)
    # TODO make this optional?
    _runCmd(["git", "clean", "-dfx"], path)


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
