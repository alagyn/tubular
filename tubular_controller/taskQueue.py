from tubular.pipeline import Pipeline
from tubular_controller.nodeConnection import NodeConnection
from tubular.task import Task


class QueueTask:

    def __init__(self, pipeline: Pipeline, task: Task,
                 availableNodes: set[NodeConnection]) -> None:
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
