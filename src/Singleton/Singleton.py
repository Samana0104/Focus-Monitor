from threading import Lock
from typing import Self


class Singleton:
    """Thread-safe base class that creates one instance per subclass."""

    _instance = None
    _instance_lock = Lock()

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._instance = None
        cls._instance_lock = Lock()

    def __new__(cls, *args, **kwargs) -> Self:
        if cls is Singleton:
            raise TypeError("Singleton must be inherited, not instantiated directly")

        if cls._instance is not None:
            return cls._instance

        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)

        return cls._instance

    @classmethod
    def get_instance(cls) -> Self:
        if cls._instance is not None:
            return cls._instance

        return cls()
