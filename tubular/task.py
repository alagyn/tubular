from typing import Dict, Any

from tubular.step import makeStep, Step
from tubular.task_env import TaskEnv


class Task:

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name = name
        try:
            self.display = config['meta']['display']
        except KeyError:
            self.display = name

        # TODO node tags

        self.steps: list[Step] = []

        stepConfigs = config['steps']
        for step in stepConfigs:
            self.steps.append(makeStep(step))

    def run(self, taskEnv: TaskEnv):
        for idx, step in enumerate(self.steps):
            print(f"Running step {step.display}")
            taskEnv.taskStep = idx
            step.run(taskEnv)
