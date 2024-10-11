import os
import uuid
from typing import Dict, Any
import threading
import time
import json

import requests

from tubular.config_loader import load_configs
from tubular import git_cmds
from tubular.pipeline import Pipeline, PipelineReq
from tubular.stage import Stage
from tubular.task import Task
from tubular_node.node import NodeStatus


class Node:

    def __init__(self, name: str, hostname: str, port: int,
                 tags: list[str]) -> None:
        self.name = name
        self.hostname = hostname
        self.port = port
        self.tags: set[str] = set(tags)
        self.status = NodeStatus.Offline

        self._url = f"http://{self.hostname}:{self.port}"

    def sendTask(self, pipeline: Pipeline, task: Task):
        print("sending task to", self.name)
        args = {
            "repo_url": pipeline.repo_url,
            "branch": pipeline.branch,
            "task_path": task.file,
            "uuid": task.uuid.hex,
            "args": pipeline.args
        }
        print(args)
        # TODO error check
        ret = requests.post(url=f'{self._url}/queue', json=args, timeout=5)
        print(ret.json())

    def updateStatus(self):
        print(f"checking '{self.name}:{self.port}'")
        try:
            ret = requests.get(
                url=f'http://{self.hostname}:{self.port}/status', timeout=5)
            self.status = NodeStatus[ret.json()['status']]
        except requests.Timeout:
            self.status = NodeStatus.Offline
        except requests.ConnectionError:
            self.status = NodeStatus.Offline
        print(self.name, self.status.name)


class PipelineRepo:

    def __init__(self, name: str, url: str, paths: list[str]) -> None:
        self.name = name
        self.url = url
        self.paths = paths


class QueueTask:

    def __init__(self, pipeline: Pipeline, task: Task,
                 availableNodes: set[Node]) -> None:
        self.pipeline = pipeline
        self.task = task
        self.availableNodes = availableNodes
        self.prev: QueueTask | None = None
        self.next: QueueTask | None = None


class TaskQueue:

    def __init__(self) -> None:
        self.front: QueueTask | None = None
        self.back: QueueTask | None = None
        self.size = 0

    def push(self, item: QueueTask):
        self.size += 1
        if self.back is None:
            self.front = item
            self.back = item
        else:
            self.back.next = item
            item.prev = self.back
            self.back = item

    def unlink(self, item: QueueTask):
        self.size -= 1
        if item is self.back:
            self.back = item.prev
        if item is self.front:
            self.front = item.next
        if item.prev is not None:
            item.prev.next = item.next
        if item.next is not None:
            item.next.prev = item.prev

    def __len__(self) -> int:
        return self.size


class ControllerState:

    def __init__(self) -> None:
        self.workspace = ""
        self.nodes: list[Node] = []
        self.pipelineRepos: list[PipelineRepo] = []

        self.shouldRun = True
        self.workerThread = threading.Thread()

        self.taskQueueCV = threading.Condition()
        self.taskQueue = TaskQueue()

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

        self.updateNodeStatus()

        self.workerThread = threading.Thread(target=self.management_thread)
        self.workerThread.start()

    def stop(self):
        self.shouldRun = False
        with self.taskQueueCV:
            self.taskQueueCV.notify()
        self.workerThread.join()

    def management_thread(self):
        while True:
            with self.taskQueueCV:
                if len(self.taskQueue) == 0:
                    self.taskQueueCV.wait()
                if not self.shouldRun:
                    break
                self.updateNodeStatus()

                cur = self.taskQueue.front
                while cur != None:
                    for node in cur.availableNodes:
                        if node.status == NodeStatus.Idle:
                            node.sendTask(cur.pipeline, cur.task)
                            self.taskQueue.unlink(cur)
                            node.status = NodeStatus.Active
                            break
                    cur = cur.next

                if len(self.taskQueue) > 0:
                    # Force sleep while waiting for nodes?
                    # TODO better ways of doing this
                    time.sleep(1)

    def queuePipeline(self, pipelineReq: PipelineReq):
        # TODO chuck this into a thread?
        repoDir = os.path.join(self.workspace, pipelineReq.getRepoPath())
        git_cmds.cloneOrPull(pipelineReq.repo_url, pipelineReq.branch, repoDir)

        pipeline = Pipeline(pipelineReq, repoDir)

        for stage in pipeline.stages:
            self.runStage(pipeline, stage)

    def runStage(self, pipeline: Pipeline, stage: Stage):
        for task in stage.tasks:
            taskUUID = uuid.uuid4()

            availableNodes: list[Node] = []
            for x in self.nodes:
                # make sure all of the whitelisted tags are present
                if len(task.whiteTags - x.tags) > 0:
                    print("missing", task.whiteTags - x.tags)
                    continue
                # make sure none of the blacklisted are there
                if len(task.blackTags & x.tags) > 0:
                    print("has", task.blackTags & x.tags)
                    continue
                availableNodes.append(x)

            if len(availableNodes) == 0:
                raise RuntimeError("No available nodes")

            with self.taskQueueCV:
                self.taskQueue.push(
                    QueueTask(pipeline, task, set(availableNodes)))
                self.taskQueueCV.notify()

    def updateNodeStatus(self):
        for node in self.nodes:
            node.updateStatus()
