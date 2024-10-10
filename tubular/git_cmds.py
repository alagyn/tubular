import subprocess as sp
import re


def clone(url: str, branch: str, output: str):
    sp.run(args=["git", "clone", url, f"--branch={branch}", output])


def pull(repo_path: str):
    sp.run(args=["git", "reset", "--hard"], cwd=repo_path)
    sp.run(args=["git", "pull"], cwd=repo_path)


def getRepoName(url: str) -> str:
    stripped = url.strip("/")
    if stripped.endswith(".git"):
        stripped = stripped[:-4]
    return stripped.split("/")[-1]
