from typing import Dict, Any


class Pipeline:

    def __init__(self, repo: str, pipeline: str, args: Dict[str, Any]) -> None:
        self.repo = repo
        self.pipeline = pipeline
        self.args = args
