import os
import shutil
from typing import Dict, Any
import threading
import time
import glob
from collections import defaultdict

import requests

from tubular.config_loader import load_configs
from tubular import git_cmds
from tubular.pipeline import Pipeline, PipelineReq, PipelineDef, formatArchiveDirName
from tubular.stage import Stage
from tubular.task import Task
from tubular_node.node import NodeStatus, PipelineStatus
from tubular.pipeline_db import PipelineDB
from tubular.file_utils import decompressArchive, decompressOutputFile, sanitizeFilepath

NODE_UPDATE_PERIOD = 2
PIPELINE_UPDATE_PERIOD = 30

# TODO cleanup old archives


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

    def sendTask(self, pipeline: Pipeline, task: Task):
        print("sending task to", self.name)
        self.currentTask = task
        args = task.toTaskReq(pipeline.args)
        requests.post(url=f'{self._url}/queue',
                      json=args.model_dump(),
                      timeout=5)

    def _downloadArchive(self, task: Task, finalStatus: PipelineStatus):
        args = task.toTaskReq({}).model_dump()

        # Download archived files
        with requests.get(url=f'{self._url}/archive', stream=True,
                          json=args) as r:
            r.raise_for_status()
            with open(task.meta.archiveZipFile, mode='wb') as f:
                for chunk in r.iter_content():
                    f.write(chunk)

        # Download output
        with requests.get(url=f'{self._url}/output', stream=True,
                          json=args) as r:
            with open(task.meta.outputZipFile, mode='wb') as f:
                for chunk in r.iter_content():
                    f.write(chunk)

        # set status here so we wait till after the download
        task.setStatus(finalStatus)

    def updateStatus(self):
        try:
            ret = requests.get(url=f'{self._url}/status', timeout=2)
            data = ret.json()

            taskStatus = PipelineStatus[data["task_status"]]

            if self.currentTask is not None and taskStatus != PipelineStatus.Running:
                threading.Thread(target=self._downloadArchive,
                                 args=(self.currentTask, taskStatus)).start()

            self.status = NodeStatus[data['status']]
        except requests.Timeout:
            self.status = NodeStatus.Offline
        except requests.ConnectionError:
            self.status = NodeStatus.Offline


class ArchiveLister:

    def __init__(self, pipeline: str, branch: str, run: int,
                 archivePath: str) -> None:
        self.pipeline = pipeline
        self.branch = branch
        self.run = run
        self.archivePath = archivePath

    def getArchiveList(self) -> dict:
        out = {}
        self._buildArchiveList("", self.archivePath, out)
        return out

    def _buildArchiveList(self, parentPath: str, curPath: str, out: dict):
        out['label'] = curPath

        children = []
        out['children'] = children

        fullPath = os.path.join(parentPath, curPath)

        for x in os.scandir(fullPath):
            if x.name == '_output':
                continue
            child = {}

            if x.is_file():
                child['label'] = x.name
                relPath = os.path.relpath(os.path.join(fullPath, x.name),
                                          self.archivePath)
                child[
                    'href'] = f'/api/archive?pipeline={self.pipeline}&branch={self.branch}&run={self.run}&file={relPath}'
            else:
                self._buildArchiveList(fullPath, x.name, child)

            children.append(child)


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

    def __init__(self, pipelines: list[PipelineDef], checkTime: float) -> None:
        self.pipelines = pipelines
        self.time = checkTime

    def getPipeline(self, path: str) -> PipelineDef | None:
        for x in self.pipelines:
            if x.file == path:
                return x
        return None


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
        self.workspace = os.path.realpath(ctrlConfigs["workspace"])

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
                            node.sendTask(cur.pipeline, cur.task)
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
        if len(pipelineReq.branch.strip()) == 0:
            pipelineReq.branch = self.pipelineRepoDefBranch
        # TODO reject queue requests if pipeline repo has an update
        threading.Thread(target=self._runPipelineThread,
                         args=(pipelineReq, )).start()

    def _runPipelineThread(self, pipelineReq: PipelineReq):
        path = self._getRepoPath(pipelineReq.branch)
        with self._branchLocks[path]:
            repoDir = self._cloneOrPullRepo(pipelineReq.branch)
            pipelineDef = PipelineDef(repoDir, pipelineReq.pipeline_path)

            pipelineID, runNum = self._db.getPipelineIDAndNextRun(
                pipelineDef.file)

            pipeline = Pipeline(self.pipelineRepoUrl, pipelineDef, pipelineReq,
                                repoDir, runNum)

            start = time.time()

            oldRuns = self._db.addRun(pipelineID, runNum, pipelineReq.branch,
                                      start, pipeline.meta.maxRuns)

            for x in oldRuns:
                folder = formatArchiveDirName(repoDir, pipeline.meta.name, x)
                if os.path.exists(folder):
                    print("Removing archive for", x)
                    shutil.rmtree(folder)

            print(pipeline.stages)

            for stage in pipeline.stages:
                self.runStage(pipeline, stage)
                if pipeline.status != PipelineStatus.Running:
                    print("Pipeline error")
                    break

            if pipeline.status == PipelineStatus.Running:
                pipeline.status = PipelineStatus.Success

            end = time.time()

            self._db.setRunStatus(pipelineID, runNum, end - start,
                                  pipeline.status)

            print(f"Pipeline complete: {pipeline.meta.display}")

    def runStage(self, pipeline: Pipeline, stage: Stage):
        for task in stage.tasks:
            availableNodes: list[Node] = []
            for x in self.nodes:
                # make sure all of the whitelisted tags are present
                if len(task.meta.whiteTags - x.tags) > 0:
                    continue
                # make sure none of the blacklisted are there
                if len(task.meta.blackTags & x.tags) > 0:
                    continue
                availableNodes.append(x)

            if len(availableNodes) == 0:
                raise RuntimeError("No available nodes")

            with self.taskQueueCV:
                self._tasksWaiting += 1
                self.taskQueue.push(
                    QueueTask(pipeline, task, set(availableNodes)))
                self.taskQueueCV.notify()

        # wait for every task to complete
        for task in stage.tasks:
            status = task.waitForComplete()
            self._tasksWaiting -= 1

            decompressArchive(task.meta.archiveZipFile, pipeline.archive)
            decompressOutputFile(task.meta.outputZipFile, pipeline.outputDir)

            if status != PipelineStatus.Success:
                pipeline.status = status

        print(f"Stage complete: {stage.meta.display}")

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

    def _updatePipelineCache(self, branch: str) -> _PipelineCache:
        print(f"updating pipeline cache {branch=}")
        path = self._cloneOrPullRepo(branch)

        pipelineFiles: list[str] = []

        for file in glob.iglob(f'**/*.yaml', root_dir=path, recursive=True):
            print("checking file", file)
            fullPath = os.path.join(path, file)
            with open(fullPath, mode='r') as f:
                for line in f:
                    match line.strip():
                        case "stages:":
                            pipelineFiles.append(file)
                            break
                        case "steps:":
                            break

        pipelines = [PipelineDef(path, x) for x in pipelineFiles]
        out = _PipelineCache(pipelines, time.time())
        self._pipelineCache[branch] = out
        return out

    def _getPipelineCache(self, branch: str) -> _PipelineCache:
        try:
            cache = self._pipelineCache[branch]
            if time.time() - cache.time > PIPELINE_UPDATE_PERIOD:
                cache = self._updatePipelineCache(branch)
            else:
                print("using cache")
        except KeyError:
            cache = self._updatePipelineCache(branch)

        return cache

    def getPipelines(self, branch: str | None) -> list[str]:
        if branch is None:
            branch = self.pipelineRepoDefBranch

        cache = self._getPipelineCache(branch)

        out = []
        for x in cache.pipelines:
            print("checking last run", x)
            pId = self._db.getPipelineId(x.file)
            run = self._db.getLastRun(pId)
            data = {"name": x.display, "path": x.file}
            if run is None:
                data["timestamp"] = "Not Run"
                data["status"] = "Not Run"
            else:
                timestamp = time.localtime(run.startTime)
                data["timestamp"] = time.strftime("%x %X", timestamp)
                data["status"] = run.status.name
            out.append(data)

        return out

    def getPipelineArgs(self, pipelinePath: str,
                        branch: str | None) -> list[dict[str, str]]:
        if branch is None:
            branch = self.pipelineRepoDefBranch
        cache = self._getPipelineCache(branch)

        pipeline = cache.getPipeline(pipelinePath)
        if pipeline is None:
            raise RuntimeError("Pipeline not found")

        return [{"k": x[0], "v": x[1]} for x in pipeline.args]

    def getRuns(self, pipelinePath: str) -> list[dict[str, Any]]:
        pId = self._db.getPipelineId(pipelinePath)
        runs = self._db.getRuns(pId)

        out = []

        for run in runs:
            timestamp = time.localtime(run.startTime)
            if run.status == PipelineStatus.Running:
                duration = time.time() - run.startTime
            else:
                duration = run.duration
            data = {
                "run": run.runNum,
                "branch": run.branch,
                "timestamp": time.strftime("%x %X", timestamp),
                "duration": round(duration, 3),
                "status": run.status.name
            }

            out.append(data)

        return out

    def getBranches(self) -> list[str]:
        return git_cmds.getBranches(self.pipelineRepoUrl)

    def getArchiveList(self, pipeline: str, branch: str, run: int) -> dict:

        repoPath = self._getRepoPath(branch)
        pipelinePath = os.path.splitext(pipeline)[0]
        archivePath = os.path.join(repoPath, f'{pipelinePath}.archive.{run}')

        x = ArchiveLister(pipeline, branch, run, archivePath)

        return x.getArchiveList()

    def getArchiveFile(self, pipeline: str, branch: str, run: int,
                       file: str) -> str:
        repoPath = self._getRepoPath(branch)
        pipelinePath = os.path.splitext(pipeline)[0]
        archivePath = os.path.join(repoPath, f'{pipelinePath}.archive.{run}')

        fullpath = sanitizeFilepath(archivePath, file)

        if not os.path.isfile(fullpath):
            raise RuntimeError(f"Path not found: '{file}'")

        return fullpath

    def getRunsStats(self) -> dict[str, Any]:
        status = self._db.getLast50RunsStatus()

        errors = 0
        fails = 0
        running = 0
        queued = 0
        success = 0

        for x in status:
            match x:
                case PipelineStatus.Error:
                    errors += 1
                case PipelineStatus.Fail:
                    fails += 1
                case PipelineStatus.Running:
                    running += 1
                case PipelineStatus.Queued:
                    queued += 1
                case PipelineStatus.Success:
                    success += 1

        return {
            "runs": {
                "error": errors,
                "fail": fails,
                "running": running,
                "queued": queued,
                "success": success
            }
        }
