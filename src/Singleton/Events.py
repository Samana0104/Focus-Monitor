from Singleton.Singleton import Singleton
from collections import defaultdict
from types import MethodType
from typing import Any, Callable
from weakref import WeakMethod

Payload = dict[str, Any]
EventHandler = Callable[[Payload], None]
StoredEventHandler = EventHandler | WeakMethod


class EventManager(Singleton):
    """Publish payloads to handlers registered under a string event key.

    Usage:
        def on_detected(payload: Payload) -> None:
            print(payload["confidence"])

        event_manager.subscribe("drowsy_detected", on_detected)
        event_manager.publish("drowsy_detected", confidence=0.95)
        event_manager.unsubscribe("drowsy_detected", on_detected)
    """

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._subscribers: dict[str, list[StoredEventHandler]] = defaultdict(list)

    @staticmethod
    def __store_handler(handler: EventHandler) -> StoredEventHandler:
        """
            이벤트 핸들러를 저장할 때 사용됩니다. 만약 핸들러가 인스턴스 메서드라면, WeakMethod로 래핑하여 저장합니다
        Args:
            handler (EventHandler): 이벤트 핸들러
        Returns:
            StoredEventHandler
        """
        if isinstance(handler, MethodType):
            return WeakMethod(handler)

        return handler

    @staticmethod
    def __resolve_handler(handler: StoredEventHandler) -> EventHandler | None:
        if isinstance(handler, WeakMethod):
            return handler()

        return handler

    def subscribe(self, key: str, handler: EventHandler) -> None:
        """Register a handler for an event key."""
        stored_handler = self.__store_handler(handler)

        if stored_handler not in self._subscribers[key]:
            self._subscribers[key].append(stored_handler)

    def unsubscribe(self, key: str, handler: EventHandler) -> None:
        """Remove a handler registered for an event key."""
        stored_handler = self.__store_handler(handler)

        handlers = self._subscribers.get(key)
        if not handlers:
            return

        try:
            handlers.remove(stored_handler)
        except ValueError:
            return

        if not handlers:
            del self._subscribers[key]

    def publish(self, key: str, **payload: Any) -> None:
        """
            사용자가 지정한 이벤트 키에 대해 등록된 모든 핸들러를 호출하고, 페이로드를 전달합니다용

            Args:
                key (str): 이벤트 키
                payload (dict): 이벤트 핸들러에 전달할 페이로드
        """
        handlers: list[EventHandler] = []

        stored_handlers: list[StoredEventHandler] | None = self._subscribers.get(key)
        if not stored_handlers:
            return

        live_handlers: list[StoredEventHandler] = []
        for stored_handler in stored_handlers:
            handler = self.__resolve_handler(stored_handler)

            if handler is not None:
                # WeakMethod가 유효한 경우에만 핸들러를 호출하도록 합니다.
                handlers.append(handler)
                # WeakMethod를 보관하기 위해 live_handlers에 추가합니다.
                live_handlers.append(stored_handler)

        if live_handlers:
            self._subscribers[key] = live_handlers
        else:
            del self._subscribers[key]

        for handler in handlers:
            handler(payload)


event_manager: EventManager = EventManager.get_instance()
