from typing import Any

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from Singleton.Singleton import Singleton


class _InputEventFilter(QObject):
    def __init__(self, owner: "Input", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._owner = owner

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        self._owner._process_event(event)
        return False


class Input(Singleton):
    """Singleton that tracks application-wide keyboard and mouse state."""

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._application: QApplication | None = None
        self._event_filter: _InputEventFilter | None = None
        self._pressed_keys: set[Any] = set()
        self._just_pressed_keys: set[Any] = set()
        self._just_released_keys: set[Any] = set()
        self._pressed_mouse_buttons: set[Any] = set()
        self._just_pressed_mouse_buttons: set[Any] = set()
        self._just_released_mouse_buttons: set[Any] = set()

    def initialize(self, application: QApplication) -> None:
        if self._application is application:
            return

        self.shutdown()
        self._application = application
        self._event_filter = _InputEventFilter(self, application)
        self._application.installEventFilter(self._event_filter)

    def shutdown(self) -> None:
        if self._application is not None and self._event_filter is not None:
            self._application.removeEventFilter(self._event_filter)
        self._application = None
        self._event_filter = None
        self.clear()

    def is_key_down(self, key: Any) -> bool:
        return self.__normalize(key) in self._pressed_keys

    def was_key_pressed(self, key: Any) -> bool:
        return self.__normalize(key) in self._just_pressed_keys

    def was_key_released(self, key: Any) -> bool:
        return self.__normalize(key) in self._just_released_keys

    def consume_key_press(self, key: Any) -> bool:
        key_code = self.__normalize(key)
        if key_code not in self._just_pressed_keys:
            return False
        self._just_pressed_keys.remove(key_code)
        return True

    def is_mouse_button_down(self, button: Any) -> bool:
        return self.__normalize(button) in self._pressed_mouse_buttons

    def was_mouse_button_pressed(self, button: Any) -> bool:
        return self.__normalize(button) in self._just_pressed_mouse_buttons

    def was_mouse_button_released(self, button: Any) -> bool:
        return self.__normalize(button) in self._just_released_mouse_buttons

    def consume_mouse_button_press(self, button: Any) -> bool:
        button_code = self.__normalize(button)
        if button_code not in self._just_pressed_mouse_buttons:
            return False
        self._just_pressed_mouse_buttons.remove(button_code)
        return True

    def end_frame(self) -> None:
        self._just_pressed_keys.clear()
        self._just_released_keys.clear()
        self._just_pressed_mouse_buttons.clear()
        self._just_released_mouse_buttons.clear()

    def clear(self) -> None:
        self._pressed_keys.clear()
        self._just_pressed_keys.clear()
        self._just_released_keys.clear()
        self._pressed_mouse_buttons.clear()
        self._just_pressed_mouse_buttons.clear()
        self._just_released_mouse_buttons.clear()

    def _process_event(self, event: QEvent) -> None:
        event_type = event.type()

        if event_type == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            if not event.isAutoRepeat():
                key_code = self.__normalize(event.key())
                if key_code not in self._pressed_keys:
                    self._just_pressed_keys.add(key_code)
                self._pressed_keys.add(key_code)

        elif event_type == QEvent.Type.KeyRelease and isinstance(event, QKeyEvent):
            if not event.isAutoRepeat():
                key_code = self.__normalize(event.key())
                self._pressed_keys.discard(key_code)
                self._just_released_keys.add(key_code)

        elif event_type == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent):
            button_code = self.__normalize(event.button())
            if button_code not in self._pressed_mouse_buttons:
                self._just_pressed_mouse_buttons.add(button_code)
            self._pressed_mouse_buttons.add(button_code)

        elif event_type == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
            button_code = self.__normalize(event.button())
            self._pressed_mouse_buttons.discard(button_code)
            self._just_released_mouse_buttons.add(button_code)

        elif event_type == QEvent.Type.ApplicationDeactivate:
            self.clear()

    @staticmethod
    def __normalize(button_key: Any) -> Any:
        return button_key.value if hasattr(button_key, "value") else button_key


input_instance: Input = Input.get_instance()
