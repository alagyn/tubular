import re

_REPL_RE = re.compile(r"@\{(?P<arg>[\w\-_]+)\}")


class ConstManager:
    constants: dict[str, str] = {}

    def __init__(self) -> None:
        raise RuntimeError()

    @classmethod
    def load(cls, constants: dict[str, str]):
        if not isinstance(constants, dict):
            raise RuntimeError("Invalid constants.yaml")
        for key, val in constants.items():
            if not isinstance(val, str):
                raise RuntimeError(f"Invalid constant value for key: {key}")

        print(constants)
        cls.constants = constants

    @classmethod
    def replace(cls, text: str, args: dict[str, str] = {}) -> str:

        def _repl(key: re.Match) -> str:
            keyStr = key.group("arg")
            try:
                # args override constants
                val = args[keyStr]
            except KeyError:
                # if not arg, check for a const
                try:
                    val = cls.constants[keyStr]
                except KeyError:
                    # if neither, return the key unchanged
                    val = key.group()
            return val

        return _REPL_RE.sub(_repl, text)
