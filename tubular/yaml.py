from yaml import load, dump
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def loadYAML(filename: str):
    with open(filename, mode='rb') as f:
        data = load(f, Loader)
    return data
