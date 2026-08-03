import sys
import System

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from AI.Detector import DetectionPipeline
from Singleton.Camera import camera_manager
from Singleton.EffectSound import effect_sound
from Singleton.Bgm import bgm_manager
from Singleton.Input import input_manager
from Singleton.Report import report_manager
from System.Define import DEBUG, DebugBox, DebugText, DetectionResult
from System.FunctionLibrary import FunctionLibrary
from System.StateMachine import FocusStateMachine
from Singleton.Settings import settings_instance
from Singleton.Timer import timer_manager
from UI.UIHandler import UIHandler

class Application:
    def __init__(self) -> None:
        self._running: bool = False
        self._detection_pipeline: DetectionPipeline = None
        self._detection_results: list[DetectionResult] = []
        self._state_machine: FocusStateMachine = FocusStateMachine()
        self._tick_callback_id: int | None = None
        self._detection_callback_id: int | None = None
        self._qt_app: QApplication = QApplication(sys.argv)
        self._ui: UIHandler = UIHandler()
        self._qt_app.lastWindowClosed.connect(self.stop)

    @property
    def is_running(self) -> bool:
        return self._running

    def initialize(self) -> None:
        """Initialize and show application resources once."""

        System.FunctionLibrary.log("Application is starting...", System.LogLevel.NONE)
        settings_instance.load()
        report_manager.clear()
        report_manager.initialize()

        self._detection_pipeline = DetectionPipeline()
        input_manager.initialize(self._qt_app)
        bgm_manager.initialize(self._qt_app)
        effect_sound.initialize(self._qt_app)
        self._ui.initialize()

    def __tick(self) -> None:
        if not self._running:
            return

        try:
            self.__update()
            self.__render()
        except Exception:
            self.stop()
            raise
        finally:
            input_manager.end_frame()

    def __update(self) -> None:
        if not DEBUG:
            return

        boxes, texts = self.__build_debug_draw_data()
        camera_manager.draw_debug_frame(boxes, texts)

    def __build_debug_draw_data(self) -> tuple[list[DebugBox], list[DebugText]]:
        boxes: list[DebugBox] = []
        texts: list[DebugText] = []
        if len(self._detection_results) < 3:
            return boxes, texts

        absence_result, eye_result, phone_result = self._detection_results[:3]
        if input_manager.is_key_down(Qt.Key.Key_1):
            face_bbox = absence_result.metadata.get("bbox")
            if face_bbox is None:
                texts.append(DebugText("FACE: NOT FOUND", (20, 30), (0, 0, 255)))
            else:
                if absence_result.triggered:
                    face_color = (0, 0, 255)
                else:
                    face_color = (0, 255, 0)
                similarity = float(absence_result.metadata.get("similarity", 0.0))
                boxes.append(DebugBox(face_bbox, face_color, f"FACE {similarity:.2f}"))

        if input_manager.is_key_down(Qt.Key.Key_2):
            if eye_result.triggered:
                eye_color = (0, 0, 255)
            else:
                eye_color = (0, 255, 255)
            ear = float(eye_result.metadata.get("ear", 0.0))
            for eye_bbox in eye_result.metadata.get("eye_boxes", []):
                boxes.append(DebugBox(eye_bbox, eye_color, f"EYE {ear:.2f}"))

        #if input_manager.is_key_down(Qt.Key.Key_3):
        if True:
            if phone_result.triggered:
                phone_color = (0, 0, 255)
            else:
                phone_color = (255, 128, 0)
            for phone in phone_result.metadata.get("boxes", []):
                confidence = float(phone.get("confidence", 0.0))
                boxes.append(DebugBox(phone["bbox"], phone_color, f"PHONE {confidence:.2f}"))

        return boxes, texts

    def __detect(self) -> None:
        if self._detection_pipeline is None:
            return

        frame = camera_manager.get_frame(copy=True)
        if frame is None:
            self._detection_results = []
            return

        self._detection_results = self._detection_pipeline.run(frame)
        focus_state = self._state_machine.update(self._detection_results)
        report_manager.record_state(focus_state)

    def __render(self) -> None:
        """Render the UI."""
        self._ui.render()

    def shutdown(self) -> None:
        """Release UI resources once."""
        if self._tick_callback_id is not None:
            timer_manager.unregister_callback(self._tick_callback_id)
            self._tick_callback_id = None

        if self._detection_callback_id is not None:
            timer_manager.unregister_callback(self._detection_callback_id)
            self._detection_callback_id = None

        timer_manager.stop()
        self._detection_pipeline = None
        self._detection_results = []
        self._state_machine.reset()
        report_manager.shutdown()
        input_manager.shutdown()
        bgm_manager.shutdown()
        effect_sound.shutdown()
        self._ui.shutdown()

    def run(self) -> int:
        """Start the Qt event loop and block until the application stops."""
        if self._running:
            FunctionLibrary.log("Application is already running.", System.LogLevel.WARNING)
            return

        self.initialize()
        self._running = True
        detection_interval_ms: int = max(1, int(settings_instance.ai_params.get("detection_interval_ms", 1000)))

        timer_manager.start()
        self._tick_callback_id = timer_manager.register_callback(self.__tick, 0, True)
        self._detection_callback_id = timer_manager.register_callback(self.__detect, detection_interval_ms, True)

        guide_message = (
            "Focus Monitor는 카메라와 온디바이스 AI를 이용해 "
            "사용자의 집중 상태를 실시간으로 확인하는 프로그램입니다.\n\n"
            "자리 비움, 졸음, 휴대폰 사용을 감지하면 알림으로 안내하며, "
            "집중 시간과 상태 변화 구간을 리포트로 확인할 수 있습니다.\n\n"
            "영상 분석은 사용 중인 기기 안에서 처리됩니다."
        )
        self._ui.show_popup(title="Focus Monitor 안내", reason=guide_message)
        try:
            return self._qt_app.exec()
        except Exception as e:
            FunctionLibrary.log(f"An error occurred during application execution: {e}", System.LogLevel.DANGER)
        finally:
            self._running = False
            self.shutdown()

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        timer_manager.stop()
        self._qt_app.quit()
        settings_instance.save()
