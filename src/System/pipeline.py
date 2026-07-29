class DetectionPipeline:
    def __init__(self, detectors: list[BaseDetector]):
        self._detectors = detectors

    def run(self, frame) -> list[DetectionResult]:
        """
        주어진 frame에 대해 detecter들의 detect 결과를 반환한다.
        """
        return [d.detect(frame) for d in self._detectors]
