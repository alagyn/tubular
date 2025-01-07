import os
import shutil
from typing import Any
import threading
import time
import glob
from collections import defaultdict
import traceback
import json

from tubular_controller.nodeConnection import NodeConnection
from tubular_controller.taskQueue import TaskQueue, QueueTask
from tubular_controller.archiveLister import ArchiveLister

from tubular.configLoader import loadMainConfig
from tubular import git_cmds
from tubular.pipeline import Pipeline, PipelineReq, PipelineDef, formatPipelineName
from tubular.stage import Stage
from tubular_node.node import NodeStatus, PipelineStatus
from tubular.pipeline_db import PipelineDB
from tubular.file_utils import decompressArchive, decompressOutputFile, sanitizeFilepath
from tubular.repo import Repo
from tubular.trigger import Trigger, makeTrigger
from tubular.yaml import loadYAML
from tubular.constantManager import ConstManager
from tubular.tempManager import TempManager

NODE_UPDATE_PERIOD = 2
PIPELINE_UPDATE_PERIOD = 30
TRIGGER_UPDATE_PERIOD = 30


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
        self.nodes: list[NodeConnection] = []

        self.configRepo: Repo = Repo("", "", "")
        self.configCommit = bytearray()

        self.pipelineRepoPath: str = ""
        self.pipelineRepoUrl = ""
        self.pipelinePaths: list[str] = []
        self.pipelineRepoDefBranch: str = "main"

        self.shouldRun = True
        self._workerThread = threading.Thread()

        self.taskQueueCV = threading.Condition()
        self.taskQueue = TaskQueue()

        self.triggerLock = threading.Semaphore()
        self._triggerThread = threading.Thread()
        self.triggers: list[Trigger] = []

        self._lastNodeCheck = 0
        self._tasksWaiting = 0

        self._pipelineCache: dict[str, _PipelineCache] = {}

        self._branchLocks: dict[str, threading.Semaphore] = defaultdict(
            threading.Semaphore)

    def start(self):
        config = loadMainConfig()

        ctrlConfigs = config["controller"]
        self.workspace = os.path.realpath(ctrlConfigs["workspace"])

        dbFile = os.path.join(self.workspace, "tubular.db")
        self._db = PipelineDB(dbFile)

        TempManager.setWorkspace(os.path.join(self.workspace, "temp"))

        configRepoUrl = config["config-repo"]
        try:
            configBranch = config["config-branch"]
        except KeyError:
            configBranch = "main"

        configDir = os.path.join(self.workspace, "tubular-configs")
        self.configRepo = Repo(configRepoUrl, configBranch, configDir)

        self.loadConfigs()

        self._workerThread = threading.Thread(
            target=self.queueManagementThread)
        self._workerThread.start()

        self._triggerThread = threading.Thread(
            target=self.triggerManagementThread)
        self._triggerThread.start()

    def stop(self):
        self.shouldRun = False
        with self.taskQueueCV:
            self.taskQueueCV.notify()
        self._workerThread.join()

    def loadConfigs(self):
        # TODO revert if config load fails
        # TODO report config load errors somewhere

        # lock both the threads if reloading live
        with self.taskQueueCV, self.triggerLock:
            remoteCommit = git_cmds.getLatestRemoteCommit(self.configRepo)
            if self.configCommit == remoteCommit:
                return
            self.configCommit = remoteCommit
            git_cmds.cloneOrPull(self.configRepo)

            # Load pipeline configs
            pipeConfigs = loadYAML(
                os.path.join(self.configRepo.path,
                             "pipelines.yaml"))['pipelines']
            self.pipelineRepoUrl = pipeConfigs["url"]
            self.pipelineRepoPath = os.path.join(
                self.workspace, git_cmds.getRepoName(self.pipelineRepoUrl))

            try:
                self.pipelineRepoDefBranch = str(pipeConfigs["default-branch"])
            except KeyError:
                pass

            # Load optional constants config
            constsFile = os.path.join(self.configRepo.path, "constants.yaml")
            if os.path.exists(constsFile):
                consts = loadYAML(constsFile)
                ConstManager.load(consts)

            # Load optional trigger config
            triggerFile = os.path.join(self.configRepo.path, "triggers.yaml")
            if os.path.exists(triggerFile):
                triggers = loadYAML(triggerFile)
                self.triggers = [makeTrigger(t) for t in triggers["triggers"]]

            # Load node configs
            nodeConfigs = loadYAML(
                os.path.join(self.configRepo.path, "nodes.yaml"))['nodes']

            for name, args in nodeConfigs.items():
                try:
                    hostname = args["host"]
                except KeyError:
                    hostname = name
                port = args["port"]
                tags = args["tags"]
                n = NodeConnection(name, hostname, port, tags)
                self.nodes.append(n)

            self.updateNodeStatus()

    def triggerManagementThread(self):
        while True:
            with self.triggerLock:
                for t in self.triggers:
                    if t.check():
                        for req in t.piplines:
                            self.queuePipeline(req)
                TempManager.freeTempDirsByPrefix("trigger")

            time.sleep(TRIGGER_UPDATE_PERIOD)

    def queueManagementThread(self):
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
            repo = self._cloneOrPullRepo(pipelineReq.branch)
            commit = git_cmds.getCurrentLocalCommit(repo)
            pipelineDef = PipelineDef(repo.path, pipelineReq.pipeline_path)

            pipelineID, runNum = self._db.getPipelineIDAndNextRun(
                pipelineDef.file)

            archivePath = self._getArchivePath(pipelineReq.branch,
                                               pipelineDef.name, runNum)
            outputPath = self._getOutputPath(pipelineReq.branch,
                                             pipelineDef.name, runNum)

            os.makedirs(archivePath)
            os.makedirs(outputPath)

            pipeline = Pipeline(
                self.pipelineRepoUrl,
                pipelineDef,
                pipelineReq,
                archivePath,
                outputPath,
            )

            start = time.time()

            oldRuns = self._db.addRun(pipelineID, runNum, pipelineReq.branch,
                                      commit, start, pipeline.meta.maxRuns)

            for x in oldRuns:
                oldArch = self._getArchivePath(pipelineReq.branch,
                                               pipeline.meta.name, x)
                oldOut = self._getOutputPath(pipelineReq.branch,
                                             pipeline.meta.name, x)
                if os.path.exists(oldArch):
                    print("Removing archive for", x)
                    shutil.rmtree(oldArch)
                    shutil.rmtree(oldOut)

            print(pipeline.stages)

            stageStatuses = [{
                "display":
                stage.meta.display,
                "stages": [{
                    "display":
                    task.meta.display,
                    "output":
                    os.path.relpath(task.outputFile, outputPath),
                    "status":
                    task.status
                } for task in stage.tasks]
            } for stage in pipeline.stages]

            try:
                for sIdx, stage in enumerate(pipeline.stages):
                    statuses = stageStatuses[sIdx]['stages']
                    self.runStage(pipeline, stage, statuses)
                    if pipeline.status != PipelineStatus.Running:
                        print("Pipeline error")
                        break
            except Exception as err:
                print("Exception occurred while running pipeline")
                traceback.print_exception(err, chain=True)
                pipeline.status = PipelineStatus.Fail

            if pipeline.status == PipelineStatus.Running:
                pipeline.status = PipelineStatus.Success

            end = time.time()

            numArchived = 0
            for x in glob.iglob("**/*", root_dir=archivePath, recursive=True):
                if not os.path.isdir(os.path.join(archivePath, x)):
                    numArchived += 1

            metadata = {"stages": stageStatuses, "numArchived": numArchived}

            self._db.setRunStatus(pipelineID, runNum, end - start,
                                  pipeline.status, json.dumps(metadata))

            print(f"Pipeline complete: {pipeline.meta.display}")

    def runStage(self, pipeline: Pipeline, stage: Stage, statuses: list[dict]):
        for task in stage.tasks:
            availableNodes: list[NodeConnection] = []
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
        for tIdx, task in enumerate(stage.tasks):
            status = task.waitForComplete()
            self._tasksWaiting -= 1

            decompressArchive(task.archiveZipFile, pipeline.archive)
            os.remove(task.archiveZipFile)
            decompressOutputFile(task.outputZipFile, pipeline.outputDir)
            os.remove(task.outputZipFile)

            if status != PipelineStatus.Success:
                pipeline.status = status

            statuses[tIdx]["status"] = status

        print(f"Stage complete: {stage.meta.display}")

    def _updateNodeStatusThread(self):
        for node in self.nodes:
            node.updateStatus()

    def updateNodeStatus(self):
        curTime = time.time()
        if curTime - self._lastNodeCheck > NODE_UPDATE_PERIOD:
            self._lastNodeCheck = curTime
            threading.Thread(target=self._updateNodeStatusThread).start()

    def getNodeStatus(self) -> dict[str, str]:
        self.updateNodeStatus()
        return {x.name: x.status.name for x in self.nodes}

    def _getBranchPath(self, branch: str) -> str:
        return os.path.join(self.pipelineRepoPath, branch)

    def _getRepoPath(self, branch: str) -> str:
        return os.path.join(self._getBranchPath(branch), "repo")

    def _getArchivePath(self, branch: str, name: str, runNum: int) -> str:
        return os.path.join(self._getBranchPath(branch), "archive",
                            f'{name}.{runNum}')

    def _getOutputPath(self, branch: str, name: str, runNum: int) -> str:
        return os.path.join(self._getBranchPath(branch), "output",
                            f'{name}.{runNum}')

    def _cloneOrPullRepo(self, branch: str) -> Repo:
        """
        Returns the path to repo
        """
        path = self._getRepoPath(branch)
        repo = Repo(self.pipelineRepoUrl, branch, path)
        git_cmds.cloneOrPull(repo)
        return repo

    def _updatePipelineCache(self, branch: str) -> _PipelineCache:
        repo = self._cloneOrPullRepo(branch)

        pipelineFiles: list[str] = []

        for file in glob.iglob(f'**/*.yaml',
                               root_dir=repo.path,
                               recursive=True):
            fullPath = os.path.join(repo.path, file)
            with open(fullPath, mode='r') as f:
                for line in f:
                    match line.strip():
                        case "stages:":
                            pipelineFiles.append(file)
                            break
                        case "steps:":
                            break

        pipelines = [PipelineDef(repo.path, x) for x in pipelineFiles]
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
            data: dict = {"name": x.display, "path": x.file}
            if run is None:
                data["timestamp"] = "Not Run"
                data["status"] = PipelineStatus.NotRun
            else:
                timestamp = time.localtime(run.startTime)
                data["timestamp"] = time.strftime("%x %X", timestamp)
                data["status"] = run.status
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
                "status": run.status
            }

            out.append(data)

        return out

    def getBranches(self) -> list[str]:
        return git_cmds.getBranches(self.pipelineRepoUrl)

    def getArchiveList(self, pipeline: str, branch: str, run: int) -> dict:
        pipelineName = formatPipelineName(pipeline)
        archivePath = self._getArchivePath(branch, pipelineName, run)

        x = ArchiveLister(pipeline, branch, run, archivePath, "archive")

        return x.getArchiveList()

    def getArchiveFile(self, pipeline: str, branch: str, run: int,
                       file: str) -> str:
        pipelineName = formatPipelineName(pipeline)
        archivePath = self._getArchivePath(branch, pipelineName, run)
        fullpath = sanitizeFilepath(archivePath, file)

        if not os.path.isfile(fullpath):
            raise RuntimeError(f"Path not found: '{file}'")

        return fullpath

    def getOutputList(self, pipeline: str, branch: str, run: int) -> dict:
        pipelineName = formatPipelineName(pipeline)
        outputPath = self._getOutputPath(branch, pipelineName, run)

        x = ArchiveLister(pipeline, branch, run, outputPath, "output")

        return x.getArchiveList()

    def getOutputFile(self, pipeline: str, branch: str, run: int,
                      file: str) -> str:
        pipelineName = formatPipelineName(pipeline)
        outputPath = self._getOutputPath(branch, pipelineName, run)
        fullpath = sanitizeFilepath(outputPath, file)

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

    def getRunMeta(self, pipeline: str, run: int) -> str:
        pId = self._db.getPipelineId(pipeline)
        metaStr = self._db.getRunMeta(pId, run)
        return metaStr
