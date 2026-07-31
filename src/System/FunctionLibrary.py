import sys
from pathlib import Path
from typing import Any
from System.Define import DEBUG, RESOURCE_PATH, LogLevel, TerminalColor

"""
전역 함수를 포함하는 클래스입니다. 
인스턴스를 생성할 수 없으며, 모든 메서드는 정적(static) 메서드로 정의되어 있습니다.
"""
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
            print(f"[{LogLevel.DANGER.name}]{TerminalColor.RED.value}Invalid log level: {level}{TerminalColor.RESET.value}")

        color = FunctionLibrary.LOG_LEVEL_COLORS[level].value
        reset = TerminalColor.RESET.value
        print(f"[{level.name}]{color}{message}{reset}")

    @staticmethod
    def get_root_path() -> Path:
        """
            프로젝트 루트 경로를 반환합니다.
            소스 모드에서는 프로젝트 루트 경로를 반환하고,
            EXE 모드에서는 실행 파일이 위치한 디렉토리 경로를 반환
        """
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent

        return Path(__file__).resolve().parents[2]

    @staticmethod
    def get_resource_path() -> Path:
        """Return the resource directory path."""
        return FunctionLibrary.get_root_path() / RESOURCE_PATH

    @staticmethod
    def get_ui_path() -> Path:
        """Return the UI resource directory path."""
        return FunctionLibrary.get_resource_path() / "ui"

    @staticmethod
    def get_audio_path() -> Path:
        """Return the audio resource directory path."""
        return FunctionLibrary.get_resource_path() / "audio"

    @staticmethod
    def get_ai_path() -> Path:
        """Return the AI resource directory path."""
        return FunctionLibrary.get_resource_path() / "ai"
