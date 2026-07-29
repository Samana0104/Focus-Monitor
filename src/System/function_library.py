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
        """
        디버그 터미널 로그를 출력합니다.

        DEBUG가 False이면 출력하지 않습니다.

        Log levels:
            LogLevel.NONE: 검은색
            LogLevel.WARNING: 노란색
            LogLevel.DANGER: 빨간색

        Args:
            message: 출력할 메시지
            level: 로그 출력 단계 및 색상
        """

        if not DEBUG:
            return

        if not isinstance(level, LogLevel):
            raise TypeError("level must be a LogLevel value")

        color = FunctionLibrary.LOG_LEVEL_COLORS[level].value
        reset = TerminalColor.RESET.value
        print(f"[{level.name}]{color}{message}{reset}")
