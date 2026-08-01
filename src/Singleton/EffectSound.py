from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QApplication

from Singleton.Settings import settings_instance
from Singleton.Singleton import Singleton
from System.Define import LogLevel
from System.FunctionLibrary import FunctionLibrary


class EffectSound(Singleton):
    """Cache and play short WAV effects through reusable channels."""

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._application: QApplication | None = None
        self._channels: dict[str, list[QSoundEffect]] = {}
        self._next_channel: dict[str, int] = {}
        self._channel_count: int = 4
        self._volume: float = 1.0
        self._muted: bool = False

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def is_muted(self) -> bool:
        return self._muted

    def initialize(self, application: QApplication) -> None:
        if self._application is application:
            return

        audio_settings = getattr(settings_instance, "audio", {})
        if not isinstance(audio_settings, dict):
            audio_settings = {}

        self._application = application
        self._channel_count = max(1, int(audio_settings.get("effect_channels", 4)))
        self.set_volume(float(audio_settings.get("effect_volume", 1.0)))
        self.set_muted(bool(audio_settings.get("effect_muted", False)))

        audio_path = FunctionLibrary.get_audio_path()
        if not audio_path.is_dir():
            FunctionLibrary.log(f"Audio directory not found: {audio_path}", LogLevel.WARNING)
            return

        for source_path in audio_path.iterdir():
            if source_path.is_file():
                self.preload(source_path.name)

    def preload(self, file_name: str) -> bool:
        source_path = FunctionLibrary.get_audio_path().joinpath(file_name)
        if not source_path.is_file():
            FunctionLibrary.log(f"Effect sound file not found: {source_path}", LogLevel.WARNING)
            return False

        if file_name in self._channels:
            return True

        if self._application is None:
            FunctionLibrary.log("EffectSound must be initialized before preload.", LogLevel.WARNING)
            return False

        source_url = QUrl.fromLocalFile(str(source_path))
        channels: list[QSoundEffect] = []
        for _ in range(self._channel_count):
            effect = QSoundEffect(self._application)
            effect.setSource(source_url)
            effect.setVolume(self._volume)
            effect.setMuted(self._muted)
            channels.append(effect)

        self._channels[file_name] = channels
        self._next_channel[file_name] = 0
        return True

    def play(self, file_name: str) -> bool:
        if not self.preload(file_name):
            return False

        channels = self._channels[file_name]
        start_index = self._next_channel[file_name]
        selected_index = start_index

        for offset in range(len(channels)):
            channel_index = (start_index + offset) % len(channels)
            if not channels[channel_index].isPlaying():
                selected_index = channel_index
                break
        else:
            channels[selected_index].stop()

        channels[selected_index].play()
        self._next_channel[file_name] = (selected_index + 1) % len(channels)
        return True

    def stop(self, file_name: str | None = None) -> None:
        channel_groups = self._channels.values() if file_name is None else [self._channels.get(file_name, [])]
        for channels in channel_groups:
            for channel in channels:
                channel.stop()

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, float(volume)))
        for channels in self._channels.values():
            for channel in channels:
                channel.setVolume(self._volume)

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        for channels in self._channels.values():
            for channel in channels:
                channel.setMuted(self._muted)

    def shutdown(self) -> None:
        self.stop()
        self._channels.clear()
        self._next_channel.clear()
        self._application = None

effect_sound : EffectSound = EffectSound.get_instance()
