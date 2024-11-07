from typing import Dict, Any
import os
import uuid

from tubular.task import TaskDef, Task, TaskRequest


class StageDef:

    def __init__(self, repoPath: str, config: Dict[str, Any]) -> None:
        self.display = config["display"]
        self.tasks: list[TaskDef] = []
        for task in config['tasks']:
            if not isinstance(task, str):
                # TODO
                raise RuntimeError()
            if task.endswith(".yaml"):
                taskFile = task
            else:
                taskFile = f'{task}.yaml'
            t = TaskDef(repoPath, taskFile)
            self.tasks.append(t)


class Stage:

    def __init__(self, stageDef: StageDef) -> None:
        self.meta = stageDef
        self.tasks: list[Task] = [Task(x) for x in stageDef.tasks]

    def __repr__(self) -> str:
        return f"Stage('{self.meta.display}')"
