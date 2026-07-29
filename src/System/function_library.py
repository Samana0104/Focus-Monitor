from typing import Any
from System.define import LogLevel, TerminalColor, DEBUG

class FunctionLibrary:
    LOG_LEVEL_COLORS = {
        LogLevel.NONE: TerminalColor.BLACK,
        LogLevel.WARNING: TerminalColor.YELLOW,
        LogLevel.DANGER: TerminalColor.RED,
    }

    def __new__(cls):
        raise TypeError("SystemFunctionLibrary cannot be instantiated")

    @staticmethod
    def log(message: Any, level: LogLevel = LogLevel.NONE) -> None:
        """Print a colored message only when DEBUG is enabled."""
        if not DEBUG:
            return

        if not isinstance(level, LogLevel):
            raise TypeError("level must be a LogLevel value")

        color = FunctionLibrary.LOG_LEVEL_COLORS[level].value
        reset = TerminalColor.RESET.value
        print(f"[{level.name}]{color}{message}{reset}")
