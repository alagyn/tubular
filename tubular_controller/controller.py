from tubular.config_loader import load_configs


class Node:

    def __init__(self, name: str, hostname: str, port: int,
                 tags: list[str]) -> None:
        self.name = name
        self.hostname = hostname
        self.port = port
        self.tags: set[str] = set(tags)


class PipelineRepo:

    def __init__(self, name: str, url: str, paths: list[str]) -> None:
        self.name = name
        self.url = url
        self.paths = paths


class ControllerState:

    def __init__(self) -> None:
        self.workspace = ""
        self.nodes: list[Node] = []
        self.pipelineRepos: list[PipelineRepo] = []

    def start(self):
        config = load_configs()

        ctrlConfigs = config["controller"]
        self.workspace = ctrlConfigs["workspace"]

        for name, args in config["pipelines"].items():
            url = args["repo"]
            paths = args["paths"]
            p = PipelineRepo(name, url, paths)
            self.pipelineRepos.append(p)

        for name, args in config['nodes'].items():
            try:
                hostname = args["host"]
            except KeyError:
                hostname = name
            port = args["port"]
            tags = args["tags"]
            n = Node(name, hostname, port, tags)
            self.nodes.append(n)

    def stop(self):
        pass
