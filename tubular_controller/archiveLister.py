import os


class ArchiveLister:

    def __init__(self, pipeline: str, branch: str, run: int, archivePath: str,
                 api: str) -> None:
        self.pipeline = pipeline
        self.branch = branch
        self.run = run
        self.archivePath = archivePath
        self.api = api

    def getArchiveList(self) -> dict:
        out = {}
        self._buildArchiveList("", self.archivePath, out)
        return out

    def _buildArchiveList(self, parentPath: str, curPath: str, out: dict):
        out['label'] = curPath

        children = []
        out['children'] = children

        fullPath = os.path.join(parentPath, curPath)

        for x in os.scandir(fullPath):
            child = {}

            if x.is_file():
                child['label'] = x.name
                relPath = os.path.relpath(os.path.join(fullPath, x.name),
                                          self.archivePath)
                child[
                    'href'] = f'/api/{self.api}?pipeline={self.pipeline}&branch={self.branch}&run={self.run}&file={relPath}'
            else:
                self._buildArchiveList(fullPath, x.name, child)

            children.append(child)
