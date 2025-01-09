from tubular.task import Task
from tubular_node.node import NodeStatus, PipelineStatus
from tubular.pipeline import Pipeline
from tubular.file_utils import ensureParents

import threading
import requests


class NodeConnection:

    def __init__(self, name: str, hostname: str, port: int,
                 tags: list[str]) -> None:
        self.name = name
        self.hostname = hostname
        self.port = port
        self.tags: set[str] = set(tags)
        self.status = NodeStatus.Offline

        self._url = f"http://{self.hostname}:{self.port}"

        self.currentTask: Task | None = None

        self._downloadThread: threading.Thread | None = None

    def sendTask(self, pipeline: Pipeline, task: Task):
        print("sending task to", self.name, task.meta.name)
        self.currentTask = task
        args = task.toTaskReq(pipeline.args)
        requests.post(url=f'{self._url}/queue',
                      json=args.model_dump(),
                      timeout=5)

    def _downloadArchive(self, task: Task, finalTaskStatus: PipelineStatus):
        args = task.toTaskReq({}).model_dump()

        # Download archived files
        ensureParents(task.archiveZipFile)
        with requests.get(url=f'{self._url}/archive', stream=True,
                          json=args) as r:
            r.raise_for_status()
            with open(task.archiveZipFile, mode='wb') as f:
                for chunk in r.iter_content():
                    f.write(chunk)

        # Download output
        ensureParents(task.outputZipFile)
        with requests.get(url=f'{self._url}/output', stream=True,
                          json=args) as r:
            with open(task.outputZipFile, mode='wb') as f:
                for chunk in r.iter_content():
                    f.write(chunk)

        # set status here so we wait till after the download
        task.setStatus(finalTaskStatus)

    def updateStatus(self, updateConfigs: bool):
        try:
            if self._downloadThread is not None:
                if self._downloadThread.is_alive():
                    # don't do anything until the download is complete
                    return
                else:
                    self._downloadThread.join()
                    self._downloadThread = None

            ret = requests.get(
                url=f'{self._url}/status?updateConfig={updateConfigs}',
                timeout=2)
            data = ret.json()

            taskStatus = PipelineStatus[data["task_status"]]

            if self.currentTask is not None and taskStatus != PipelineStatus.Running and taskStatus != PipelineStatus.NotRun:
                self._downloadThread = threading.Thread(
                    target=self._downloadArchive,
                    args=(self.currentTask, taskStatus))
                self._downloadThread.start()
                self.status = NodeStatus.Archiving
                self.currentTask = None
            else:
                self.status = NodeStatus[data['status']]
        except requests.Timeout:
            self.status = NodeStatus.Offline
        except requests.ConnectionError:
            self.status = NodeStatus.Offline
