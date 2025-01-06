from yaml import load, dump
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def loadYAML(filename: str):
    with open(filename, mode='rb') as f:
        data = load(f, Loader)
    return data


def getStr(config, key) -> str:
    val = config[key]
    if not isinstance(val, str):
        raise RuntimeError(
            f"Invalid entry for {key}, expected string got: {val}")
    return val
