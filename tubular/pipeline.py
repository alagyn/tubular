from typing import Dict, Any


class Pipeline:

    def __init__(self, name: str, args: Dict[str, Any]) -> None:
        self.name = name
        try:
            self.display = args['meta']['display']
        except KeyError:
            self.display = name

        self.args = args
        self.stages = []

    def run(self):
        pass
