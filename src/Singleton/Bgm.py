from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QApplication

from Singleton.Settings import settings_instance
from Singleton.Singleton import Singleton
from System.Define import LogLevel
from System.FunctionLibrary import FunctionLibrary


class Bgm(Singleton):
    """Singleton that owns and controls background-music playback."""

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None
        self._volume: float = 0.5
        self._muted: bool = False
        self._cached_file_name: str = ""


    @property
    def is_playing(self) -> bool:
        return self._player is not None and self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def is_muted(self) -> bool:
        return self._muted

    def initialize(self, application: QApplication) -> None:
        if self._player is not None:
            return

        audio_settings = getattr(settings_instance, "audio", {})
        if not isinstance(audio_settings, dict):
            audio_settings = {}

        self._audio_output = QAudioOutput(application)
        self._audio_output.setVolume(self._volume)
        self._audio_output.setMuted(self._muted)

        self.set_volume(float(audio_settings.get("bgm_volume", 0.5)))
        self.set_muted(bool(audio_settings.get("bgm_muted", False)))

        self._player = QMediaPlayer(application)
        self._player.setAudioOutput(self._audio_output)
        self._player.errorOccurred.connect(self.__on_error)
        self._player.setPlaybackRate(1.0)

    def play(self, file_name: str, loop: bool = False) -> bool:
        """
            파일 이름이 유효한지 확인하고, BGM을 재생합니다. 파일 이름이 비어있거나 잘못된 경우, 경고 로그를 남기고 False를 반환합니다.
            :param file_name: 재생할 BGM 파일 이름
            :param loop: BGM을 반복 재생할지 여부
            :return: 재생 성공 여부 (True/False)
        """

        if self._player is None:
            FunctionLibrary.log("Bgm must be initialized before playback.", LogLevel.WARNING)
            return False

        source_path = FunctionLibrary.get_audio_path().joinpath(file_name)
        if not source_path.is_file():
            FunctionLibrary.log(f"BGM file not found: {source_path}", LogLevel.WARNING)
            return False

        if self.is_playing and self._cached_file_name == file_name:
            return False

        if self._cached_file_name != file_name:
            self._player.setSource(QUrl.fromLocalFile(str(source_path)))
            self._cached_file_name = file_name
        else:
            self._player.setPosition(0)

        loops = QMediaPlayer.Loops.Infinite if loop else QMediaPlayer.Loops.Once
        self._player.setLoops(loops)
        self._player.play()

        return True

    def pause(self) -> None:
        if self._player is not None:
            self._player.pause()

    def resume(self) -> None:
        if self._player is not None and not self._player.source().isEmpty():
            self._player.play()

    def stop(self) -> None:
        if self._player is not None:
            self._player.stop()

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._audio_output is not None:
            self._audio_output.setVolume(self._volume)

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        if self._audio_output is not None:
            self._audio_output.setMuted(self._muted)

    def shutdown(self) -> None:
        if self._player is not None:
            self._player.stop()
            self._player.setSource(QUrl())
        self._cached_file_name = ""

    def __on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        if error == QMediaPlayer.Error.NoError:
            return

        message = error_string or f"BGM playback error: {error.name}"
        FunctionLibrary.log(message, LogLevel.DANGER)


bgm_instance: Bgm = Bgm.get_instance()
