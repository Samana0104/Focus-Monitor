from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from Singleton.Bgm import bgm_manager
from Singleton.EffectSound import effect_sound
from Singleton.Settings import settings_instance


class UISettingsDialog(QDialog):
    AUDIO_PARAMETERS = (
        ("bgm_volume", "배경 음악", "배경 음악의 재생 음량입니다."),
        ("effect_volume", "알림 효과음", "집중력 알림 효과음의 재생 음량입니다."),
    )

    AI_PARAMETERS = (
        ("detection_interval_ms", "감지 주기 (ms)", "AI 감지를 실행할 간격입니다.", 100, 5000, 1),
        ("ear_threshold", "눈 감김 기준 (EAR)", "값이 높을수록 눈 감김에 민감하게 반응합니다.", 0, 100, 100),
        ("similarity_threshold", "얼굴 유사도", "값이 높을수록 등록된 얼굴 판정을 엄격하게 합니다.", 0, 100, 100),
        ("cell_phone_class", "휴대폰 클래스 ID", "YOLO에서 휴대폰으로 분류할 클래스 번호입니다.", 0, 100, 1),
        ("phone_confidence_threshold", "휴대폰 신뢰도", "값이 높을수록 확실한 휴대폰만 감지합니다.", 0, 100, 100),
        ("phone_face_distance_threshold", "휴대폰 거리 기준", "값이 높을수록 얼굴에서 먼 휴대폰도 감지합니다.", 0, 50, 10),
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("uiSettingsDialog")
        self.setWindowTitle("설정")

        root_layout: QVBoxLayout = QVBoxLayout(self)
        root_layout.setContentsMargins(32, 30, 32, 28)
        root_layout.setSpacing(12)

        audio_group: QGroupBox = QGroupBox("소리 볼륨", self)
        audio_group.setObjectName("audioVolumeGroup")
        audio_layout: QVBoxLayout = QVBoxLayout(audio_group)
        audio_layout.setContentsMargins(20, 28, 20, 20)
        audio_layout.setSpacing(18)

        for key, title, description in self.AUDIO_PARAMETERS:
            audio_layout.addWidget(self.__create_audio_row(key, title, description))

        parameter_group: QGroupBox = QGroupBox("AI 파라미터", self)
        parameter_group.setObjectName("aiParameterGroup")
        parameter_layout: QVBoxLayout = QVBoxLayout(parameter_group)
        parameter_layout.setContentsMargins(20, 28, 20, 20)
        parameter_layout.setSpacing(18)

        for key, title, description, minimum, maximum, scale in self.AI_PARAMETERS:
            parameter_layout.addWidget(self.__create_parameter_row(key, title, description, minimum, maximum, scale))

        root_layout.addWidget(audio_group)
        root_layout.addWidget(parameter_group, 1)

        done_button: QPushButton = QPushButton("완료", self)
        done_button.setObjectName("settingsDoneButton")
        done_button.clicked.connect(self.__save_and_close)
        root_layout.addWidget(done_button)

    def closeEvent(self, event: QCloseEvent) -> None:
        settings_instance.save()
        super().closeEvent(event)

    def __create_audio_row(self, key: str, title: str, description: str) -> QWidget:
        audio_settings = getattr(settings_instance, "audio", {})
        if not isinstance(audio_settings, dict):
            audio_settings = {}
            settings_instance.audio = audio_settings

        default_volume = 0.5 if key == "bgm_volume" else 1.0
        volume = max(0.0, min(1.0, float(audio_settings.get(key, default_volume))))

        row, control_layout = self.__create_slider_row(title, description)
        value_label: QLabel = QLabel(row)
        value_label.setObjectName("parameterValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slider: QSlider = QSlider(Qt.Orientation.Horizontal, row)
        slider.setObjectName("parameterSlider")
        slider.setRange(0, 100)
        slider.setValue(round(volume * 100))
        value_label.setText(f"{slider.value()}%")
        slider.valueChanged.connect(lambda value, setting_key=key, label=value_label: self.__update_audio_volume(setting_key, value, label))
        slider.sliderReleased.connect(settings_instance.save)
        control_layout.addWidget(value_label, alignment=Qt.AlignmentFlag.AlignRight)
        control_layout.addWidget(slider)
        control_layout.addStretch(1)
        return row

    def __create_parameter_row(self, key: str, title: str, description: str, minimum: int, maximum: int, scale: int) -> QWidget:
        row, control_layout = self.__create_slider_row(title, description)
        value_label: QLabel = QLabel(row)
        value_label.setObjectName("parameterValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slider: QSlider = QSlider(Qt.Orientation.Horizontal, row)
        slider.setObjectName("parameterSlider")
        slider.setRange(minimum, maximum)
        slider.setValue(round(float(settings_instance.ai_params[key]) * scale))
        value_label.setText(self.__format_value(slider.value(), scale))
        slider.valueChanged.connect(lambda value, setting_key=key, value_scale=scale, label=value_label: self.__update_parameter(setting_key, value, value_scale, label))
        slider.sliderReleased.connect(settings_instance.save)
        control_layout.addWidget(value_label, alignment=Qt.AlignmentFlag.AlignRight)
        control_layout.addWidget(slider)
        control_layout.addStretch(1)
        return row

    def __create_slider_row(self, title: str, description: str) -> tuple[QFrame, QVBoxLayout]:
        row: QFrame = QFrame(self)
        row.setObjectName("parameterRow")
        row_layout: QHBoxLayout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(18)

        info_widget: QWidget = QWidget(row)
        info_layout: QVBoxLayout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(5)
        title_label: QLabel = QLabel(title, info_widget)
        title_label.setObjectName("parameterTitle")
        description_label: QLabel = QLabel(description, info_widget)
        description_label.setObjectName("parameterDescription")
        description_label.setWordWrap(True)
        info_layout.addWidget(title_label)
        info_layout.addWidget(description_label)
        info_layout.addStretch(1)

        control_widget: QWidget = QWidget(row)
        control_layout: QVBoxLayout = QVBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(14)

        row_layout.addWidget(info_widget, 3)
        row_layout.addWidget(control_widget, 2)
        return row, control_layout

    def __update_audio_volume(self, key: str, value: int, value_label: QLabel) -> None:
        volume = value / 100
        settings_instance.audio[key] = volume
        value_label.setText(f"{value}%")

        if key == "bgm_volume":
            bgm_manager.set_volume(volume)
        else:
            effect_sound.set_volume(volume)

    def __update_parameter(self, key: str, value: int, scale: int, value_label: QLabel) -> None:
        converted_value = value if scale == 1 else value / scale
        settings_instance.ai_params[key] = converted_value
        value_label.setText(self.__format_value(value, scale))

    @staticmethod
    def __format_value(value: int, scale: int) -> str:
        if scale == 1:
            return str(value)
        if scale == 10:
            return f"{value / scale:.1f}"
        return f"{value / scale:.2f}"

    def __save_and_close(self, checked: bool = False) -> None:
        settings_instance.save()
        self.accept()
