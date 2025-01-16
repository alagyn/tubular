from typing import Any
import subprocess as sp
import os

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        SOURCE_DIR = os.path.abspath(os.path.dirname(__file__))

        print("Building Frontend")

        workdir = os.path.join(SOURCE_DIR, "tubular-frontend")

        sp.call(["npm", "install", "."], cwd=workdir)

        sp.call(["npm", "run", "build"], cwd=workdir)

        print("Built Frontend")
