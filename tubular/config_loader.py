import os

from yaml import load, dump
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def load_configs():
    try:
        cfgFile = os.environ["TUBULAR_CONFIG"]
    except KeyError:
        cfgFile = "tubular.yaml"

    if not os.path.exists(cfgFile):
        raise RuntimeError(
            f"Cannot find config file: {cfgFile}, or TUBULAR_CONFIG variable not defined"
        )

    with open(cfgFile, mode='wb') as f:
        config = load(f, Loader)
    return config
