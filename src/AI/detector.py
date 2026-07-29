from abc import ABC, abstractmethod
from System.define import DetectionResult

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, frame) -> DetectionResult:
        ...
class EyeDetecter(BaseDetector):
    def __init__(self):
        pass

    def detect(self, frame) -> DetectionResult:
        pass

class GazeDetecter(BaseDetector):
    def __init__(self):
        pass

    def detect(self, frame) -> DetectionResult:
        pass

class PhoneDetecter(BaseDetector):
    def __init__(self):
        pass

    def detect(self, frame) -> DetectionResult:
        pass
