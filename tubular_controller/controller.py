import os

from pydantic import BaseModel
from typing import Dict, Any

from tubular.config_loader import load_configs
from tubular import git_cmds
from tubular.yaml import loadYAML
from tubular.pipeline import Pipeline


class Node:

    def __init__(self, name: str, hostname: str, port: int,
                 tags: list[str]) -> None:
        self.name = name
        self.hostname = hostname
        self.port = port
        self.tags: set[str] = set(tags)


class PipelineRepo:

    def __init__(self, name: str, url: str, paths: list[str]) -> None:
        self.name = name
        self.url = url
        self.paths = paths


class PipelineReq(BaseModel):
    repo_url: str
    branch: str
    pipeline_path: str
    args: Dict[str, str]

    def getRepoPath(self):
        return os.path.join(git_cmds.getRepoName(self.repo_url), self.branch)


class ControllerState:

    def __init__(self) -> None:
        self.workspace = ""
        self.nodes: list[Node] = []
        self.pipelineRepos: list[PipelineRepo] = []

    def start(self):
        config = load_configs()

        ctrlConfigs = config["controller"]
        self.workspace = ctrlConfigs["workspace"]

        for name, args in config["pipelines"].items():
            url = args["repo"]
            paths = args["paths"]
            p = PipelineRepo(name, url, paths)
            self.pipelineRepos.append(p)

        for name, args in config['nodes'].items():
            try:
                hostname = args["host"]
            except KeyError:
                hostname = name
            port = args["port"]
            tags = args["tags"]
            n = Node(name, hostname, port, tags)
            self.nodes.append(n)

    def stop(self):
        pass

    def queuePipeline(self, pipelineReq: PipelineReq):
        repoDir = os.path.join(self.workspace, pipelineReq.getRepoPath())
        git_cmds.cloneOrPull(pipelineReq.repo_url, pipelineReq.branch, repoDir)

        pipeFile = os.path.join(repoDir, pipelineReq.pipeline_path)
        pipeName = os.path.splitext(pipelineReq.pipeline_path)[0]
        pipeConfig = loadYAML(pipeFile)
        pipeline = Pipeline(pipeName, pipeConfig)
