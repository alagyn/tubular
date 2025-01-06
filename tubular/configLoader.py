import os

from tubular.yaml import loadYAML


def loadMainConfig():
    try:
        cfgFile = os.environ["TUBULAR_CONFIG"]
    except KeyError:
        cfgFile = "tubular.yaml"

    if not os.path.exists(cfgFile):
        raise RuntimeError(
            f"Cannot find config file: {cfgFile}, or TUBULAR_CONFIG variable not defined"
        )

    return loadYAML(cfgFile)
