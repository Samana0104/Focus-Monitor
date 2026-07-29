from abc import ABC, abstractmethod
from System.define import DetectionResult

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, frame) -> DetectionResult:
        ...
class EyeDetecter(BaseDetecter):
    def __init__(self):
        pass

    def detect(self, frame) -> DetectionResult:
        pass

class GazeDetecter(BaseDetecter):
    def __init__(self):
        pass

    def detect(self, frame) -> DetectionResult:
        pass

class PhoneDetecter(BaseDetecter):
    def __init__(self):
        pass

    def detect(self, frame) -> DetectionResult:
        pass
