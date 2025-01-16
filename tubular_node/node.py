import threading
import os
import shutil

from tubular.yaml import loadYAML
from tubular import git_cmds
from tubular.task import Task, TaskDef, TaskRequest
from tubular.enums import NodeStatus, PipelineStatus
from tubular.taskEnv import TaskEnv
from tubular.file_utils import compressArchive, compressOutputFile
from tubular.repo import Repo
from tubular.tempManager import TempManager
from tubular.constantManager import ConstManager

# TODO clean up old pipeline repos/branches?


class NodeState:

    def __init__(self) -> None:
        self.workspace = ""
        self.status = NodeStatus.Idle
        self.workerThread = threading.Thread()
        self.taskStatus = PipelineStatus.Success

        self.configRepo = Repo("", "", "")
        self.configCommit = bytearray()

        self.needUpdateConfig = False

    def start(self):
        try:
            self.workspace = os.path.join(
                os.path.realpath(os.environ["TUBULAR_WORKSPACE"]), "node")
        except KeyError:
            raise RuntimeError("Please set TUBULAR_WORKSPACE env var")

        if not os.path.exists(self.workspace):
            os.makedirs(self.workspace, exist_ok=True)

        try:
            configRepoUrl = os.environ["TUBULAR_CONFIG_REPO"]
        except KeyError:
            raise RuntimeError("Please set TUBULAR_CONFIG_REPO env var")

        try:
            configBranch = os.environ["TUBULAR_CONFIG_REPO_BRANCH"]
        except KeyError:
            configBranch = "main"
        configDir = os.path.join(self.workspace, "tubular-configs")
        self.configRepo = Repo(configRepoUrl, configBranch, configDir)
        self.loadConfigs()

    def loadConfigs(self):
        remoteCommit = git_cmds.getLatestRemoteCommit(self.configRepo)
        if self.configCommit == remoteCommit:
            return
        print("Loading configs")
        self.configCommit = remoteCommit
        git_cmds.cloneOrPull(self.configRepo)

        # Load optional constants config
        constsFile = os.path.join(self.configRepo.path, "constants.yaml")
        if os.path.exists(constsFile):
            consts = loadYAML(constsFile)
            ConstManager.load(consts)

        TempManager.setWorkspace(os.path.join(self.workspace, "temp"))

    def stop(self):
        if self.workerThread.is_alive():
            self.workerThread.join()

    def queueTask(self, task: TaskRequest):
        if self.status == NodeStatus.Active:
            raise RuntimeError("Task already running")

        self.taskStatus = PipelineStatus.Running

        self.status = NodeStatus.Active
        self.workerThread = threading.Thread(
            target=self.runTask,
            args=(task, ),
        )
        self.workerThread.start()

    def runTask(self, taskReq: TaskRequest):
        # always attempt to update configs before starting a task
        if self.needUpdateConfig:
            self.loadConfigs()
            self.needUpdateConfig = False

        repoDir = os.path.join(self.workspace, taskReq.getRepoPath())
        repo = Repo(taskReq.repo_url, taskReq.branch, repoDir)
        try:
            git_cmds.cloneOrPull(repo)
            taskDef = TaskDef(repoDir, taskReq.task_path)
            taskWorkspace = os.path.join(repoDir, f'{taskDef.name}.workspace')
            taskArchive = os.path.join(repoDir, f'{taskDef.name}.archive')
            taskOutput = os.path.join(repoDir, f'{taskDef.name}.output')
            task = Task(taskReq.repo_url, taskReq.branch, taskDef, taskArchive,
                        taskOutput)
        except:
            self.taskStatus = PipelineStatus.Error
            raise

        if not os.path.isdir(taskWorkspace):
            os.makedirs(taskWorkspace, exist_ok=True)

        # Create archive dir
        os.makedirs(taskArchive, exist_ok=True)

        taskEnv = TaskEnv(taskWorkspace, taskArchive, taskOutput, taskReq.args)
        taskEnv.start()

        try:
            task.run(taskEnv)
            self.taskStatus = PipelineStatus.Success
        except:
            self.taskStatus = PipelineStatus.Fail
        print("Task complete")

        compressArchive(taskArchive, f'{taskArchive}.zip')
        compressOutputFile(taskOutput)

        # Clear archive dir
        shutil.rmtree(taskArchive)
        # Clear output file

        self.status = NodeStatus.Idle

    def getArchiveFile(self, taskReq: TaskRequest):
        repoDir = os.path.join(self.workspace, taskReq.getRepoPath())
        task = TaskDef(repoDir, taskReq.task_path)
        return os.path.join(repoDir, f'{task.name}.archive.zip')

    def getOutputFile(self, taskReq: TaskRequest):
        repoDir = os.path.join(self.workspace, taskReq.getRepoPath())
        task = TaskDef(repoDir, taskReq.task_path)

        return os.path.join(repoDir, f'{task.name}.output.zip')
