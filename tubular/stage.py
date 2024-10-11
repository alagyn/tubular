from typing import Dict, Any
import os
import uuid

from tubular.task import Task, TaskRequest


class Stage:

    def __init__(self, repo_url: str, branch: str, repoPath: str,
                 config: Dict[str, Any], args) -> None:
        self.display = config["display"]
        self.tasks: list[Task] = []
        for task in config['tasks']:
            if not isinstance(task, str):
                # TODO
                raise RuntimeError()
            if task.endswith(".yaml"):
                taskFile = task
            else:
                taskFile = f'{task}.yaml'
            req = TaskRequest(
                repo_url=repo_url,
                branch=branch,
                task_path=taskFile,
                args=args,
                uuid=uuid.uuid4(),
            )
            self.tasks.append(Task(req, repoPath))
