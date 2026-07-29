import json
from typing import Any
from pathlib import Path
from Singleton.Singleton import Singleton
from System.Define import LogLevel, SETTING_PATH
from System.FunctionLibrary import FunctionLibrary

class Settings(Singleton):
    def __init__(self):
        if getattr(self, "_initialized", False):
            FunctionLibrary.log("Settings instance already initialized.", LogLevel.DANGER)
            return

        self._initialized : bool = True
        self._file_path: Path = FunctionLibrary.get_root_path() / SETTING_PATH

        self.load()

    def __getitem__(self, key: str) -> Any:
        """Get a setting value by key."""
        value = getattr(self, key, None)
        if value is None:
            FunctionLibrary.log(f"Setting '{key}' not found.", LogLevel.WARNING)
            return None

        return value

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a setting value by key."""
        FunctionLibrary.log(f"Setting '{key}' updated to '{value}'.", LogLevel.NONE)
        setattr(self, key, value)

    def load(self) -> None:
        """
            환경설정 JSON 파일을 읽어와서 Settings 인스턴스에 적용합니다.
        """
        try:
            with open(self._file_path, "r", encoding="utf-8") as file:
                data: Any = json.load(file)
        except FileNotFoundError:
            FunctionLibrary.log(f"Settings file not found at '{self._file_path}'. Using default settings.", LogLevel.WARNING)
            return

        if not isinstance(data, dict):
            FunctionLibrary.log(f"Settings file '{self._file_path}' is not a valid JSON object.", LogLevel.DANGER)
            return

        for name, value in data.items():
            if not isinstance(name, str):
                continue

            setattr(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        """
            Settings 인스턴스의 공개 속성을 딕셔너리로 반환합니다.
        """
        return { name: value for name, value in vars(self).items() if not name.startswith("_") }

    def save(self) -> None:
        """
            Settings 인스턴스의 현재 상태를 JSON 파일로 저장합니다.
        """
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self._file_path, "w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=4, ensure_ascii=False)

settings_instance : Settings = Settings.get_instance()
