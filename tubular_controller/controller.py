import os
import uuid
from typing import Dict, Any
import threading
import time
import glob
from collections import defaultdict

import requests

from tubular.config_loader import load_configs
from tubular import git_cmds
from tubular.pipeline import Pipeline, PipelineReq
from tubular.stage import Stage
from tubular.task import Task
from tubular_node.node import NodeStatus, PipelineStatus
from tubular.pipeline_db import PipelineDB

NODE_UPDATE_PERIOD = 2
PIPELINE_UPDATE_PERIOD = 30


class Node:

    def __init__(self, name: str, hostname: str, port: int,
                 tags: list[str]) -> None:
        self.name = name
        self.hostname = hostname
        self.port = port
        self.tags: set[str] = set(tags)
        self.status = NodeStatus.Offline

        self._url = f"http://{self.hostname}:{self.port}"

        self.currentTask: Task | None = None

    def sendTask(self, url: str, pipeline: Pipeline, task: Task):
        print("sending task to", self.name)
        self.currentTask = task
        args = {
            "repo_url": url,
            "branch": pipeline.branch,
            "task_path": task.file,
            "args": pipeline.args
        }
        # TODO error check
        requests.post(url=f'{self._url}/queue', json=args, timeout=5)

    def updateStatus(self):
        try:
            ret = requests.get(url=f'{self._url}/status', timeout=2)
            data = ret.json()
            self.status = NodeStatus[data['status']]

            taskStatus = PipelineStatus[data["task_status"]]

            if self.currentTask is not None and taskStatus != PipelineStatus.Running:
                self.currentTask.setStatus(taskStatus)
        except requests.Timeout:
            self.status = NodeStatus.Offline
        except requests.ConnectionError:
            self.status = NodeStatus.Offline


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


class _PipelineCache:

    def __init__(self, pipelines: list[str], checkTime: float) -> None:
        self.pipelines = pipelines
        self.time = checkTime


class ControllerState:

    def __init__(self) -> None:
        self.workspace = ""
        self.nodes: list[Node] = []

        self.pipelineRepoPath: str = ""
        self.pipelineRepoUrl = ""
        self.pipelinePaths: list[str] = []
        self.pipelineRepoDefBranch: str = "main"

        self.shouldRun = True
        self._workerThread = threading.Thread()

        self.taskQueueCV = threading.Condition()
        self.taskQueue = TaskQueue()

        self._lastNodeCheck = 0
        self._tasksWaiting = 0

        self._pipelineCache: dict[str, _PipelineCache] = {}

        self._branchLocks: dict[str, threading.Semaphore] = defaultdict(
            threading.Semaphore)

    def start(self):
        config = load_configs()

        ctrlConfigs = config["controller"]
        self.workspace = ctrlConfigs["workspace"]

        git_cmds.initWorkspace(self.workspace)

        dbFile = os.path.join(self.workspace, "tubular.db")
        self._db = PipelineDB(dbFile)

        pipeConfigs = config["pipelines"]
        self.pipelineRepoUrl = pipeConfigs["url"]
        self.pipelineRepoPath = os.path.join(
            self.workspace, git_cmds.getRepoName(self.pipelineRepoUrl))

        try:
            self.pipelineRepoDefBranch = str(pipeConfigs["default-branch"])
        except KeyError:
            pass

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

        self._workerThread = threading.Thread(target=self.management_thread)
        self._workerThread.start()

    def stop(self):
        self.shouldRun = False
        with self.taskQueueCV:
            self.taskQueueCV.notify()
        self._workerThread.join()

    def management_thread(self):
        while True:
            needSleep = False
            with self.taskQueueCV:
                if len(self.taskQueue) == 0 and self._tasksWaiting == 0:
                    self.taskQueueCV.wait()
                if not self.shouldRun:
                    break
                self.updateNodeStatus()

                cur = self.taskQueue.front
                while cur != None:
                    for node in cur.availableNodes:
                        if node.status == NodeStatus.Idle:
                            node.sendTask(self.pipelineRepoUrl, cur.pipeline,
                                          cur.task)
                            self.taskQueue.unlink(cur)
                            node.status = NodeStatus.Active
                            break
                    cur = cur.next

                if len(self.taskQueue) > 0:
                    # Force sleep while waiting for nodes?
                    # TODO probably better ways of doing this
                    needSleep = True

            # do this outside the mutex
            if needSleep:
                time.sleep(1)

    def queuePipeline(self, pipelineReq: PipelineReq):
        threading.Thread(target=self._runPipelineThread,
                         args=(pipelineReq, )).start()

    def _runPipelineThread(self, pipelineReq: PipelineReq):
        path = self._getRepoPath(pipelineReq.branch)
        with self._branchLocks[path]:
            repoDir = self._cloneOrPullRepo(pipelineReq.branch)
            pipeline = Pipeline(self.pipelineRepoUrl, pipelineReq, repoDir)

            pipelineID, runNum = self._db.getPipelineIDAndNextRun(
                pipeline.path)

            start = time.time()

            self._db.addRun(pipelineID, runNum, pipelineReq.branch, start,
                            pipeline.maxRuns)

            for stage in pipeline.stages:
                self.runStage(pipeline, stage)
                if pipeline.status != PipelineStatus.Running:
                    break

            if pipeline.status == PipelineStatus.Running:
                pipeline.status = PipelineStatus.Success

            end = time.time()

            self._db.setRunStatus(pipelineID, runNum, end - start,
                                  pipeline.status)

            print(f"Pipeline complete: {pipeline.display}")

    def runStage(self, pipeline: Pipeline, stage: Stage):
        for task in stage.tasks:
            availableNodes: list[Node] = []
            for x in self.nodes:
                # make sure all of the whitelisted tags are present
                if len(task.whiteTags - x.tags) > 0:
                    continue
                # make sure none of the blacklisted are there
                if len(task.blackTags & x.tags) > 0:
                    continue
                availableNodes.append(x)

            if len(availableNodes) == 0:
                raise RuntimeError("No available nodes")

            with self.taskQueueCV:
                self.taskQueue.push(
                    QueueTask(pipeline, task, set(availableNodes)))
                self.taskQueueCV.notify()

        # wait for every task to complete
        for task in stage.tasks:
            with self.taskQueueCV:
                self._tasksWaiting += 1
                # Make sure the thread is unlocked
                self.taskQueueCV.notify()
            status = task.waitForComplete()
            self._tasksWaiting -= 1

            # TODO retrieve artifacts?
            # probably throw into another thread?
            # lets us copy stuff while other tasks complete

            if status != PipelineStatus.Success:
                pipeline.status = status

        print(f"Stage complete: {stage.display}")

    def updateNodeStatus(self):
        curTime = time.time()
        if curTime - self._lastNodeCheck > NODE_UPDATE_PERIOD:
            self._lastNodeCheck = curTime
            for node in self.nodes:
                node.updateStatus()

    def getNodeStatus(self) -> dict[str, str]:
        self.updateNodeStatus()
        return {x.name: x.status.name for x in self.nodes}

    def _getRepoPath(self, branch: str) -> str:
        return os.path.join(self.pipelineRepoPath, branch)

    def _cloneOrPullRepo(self, branch: str) -> str:
        """
        Returns the path to repo
        """
        path = self._getRepoPath(branch)
        git_cmds.cloneOrPull(self.pipelineRepoUrl, branch, path)
        return path

    def _getPipelineCache(self, branch: str) -> _PipelineCache:
        print(f"updating pipeline cache {branch=}")
        path = self._cloneOrPullRepo(branch)

        pipelines: list[str] = []

        for file in glob.iglob(f'{path}/**.yaml', recursive=True):
            print("checking file", file)
            with open(file, mode='r') as f:
                for line in f:
                    match line.strip():
                        case "stages:":
                            pipelines.append(file)
                            break
                        case "steps:":
                            break

        pipelines = [os.path.relpath(x, path) for x in pipelines]
        out = _PipelineCache(pipelines, time.time())
        self._pipelineCache[branch] = out
        return out

    def getPipelines(self, branch: str | None) -> list[str]:
        if branch is None:
            branch = self.pipelineRepoDefBranch

        try:
            cache = self._pipelineCache[branch]
            if time.time() - cache.time > PIPELINE_UPDATE_PERIOD:
                cache = self._getPipelineCache(branch)
            else:
                print("using cache")
        except KeyError:
            cache = self._getPipelineCache(branch)

        out = []
        for x in cache.pipelines:
            print("checking last run", x)
            pId = self._db.getPipelineId(x)
            run = self._db.getLastRun(pId)
            data = {"name": x}
            if run is None:
                data["timestamp"] = "Not Run"
                data["status"] = "Not Run"
            else:
                timestamp = time.localtime(run.startTime)
                data["timestamp"] = time.strftime("%x %X", timestamp)
                data["status"] = run.status.name
            out.append(data)

        return out

    def getRuns(self, pipelinePath: str) -> list[dict[str, Any]]:
        pId = self._db.getPipelineId(pipelinePath)
        runs = self._db.getRuns(pId)

        out = []

        for run in runs:
            timestamp = time.localtime(run.startTime)
            out.append({
                "run": run.runNum,
                "branch": run.branch,
                "timestamp": time.strftime("%x %X", timestamp),
                "duration": run.duration,
                "status": run.status.name
            })

        return out
