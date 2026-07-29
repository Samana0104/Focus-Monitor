from abc import ABC, abstractmethod
from System.define import DetectionResult, EAR_THRESHOLD

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2  

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, frame) -> DetectionResult:
        ...

class DetectionPipeline:
    def __init__(self):
        self._detectors = [
            EyeDetecter(),
            GazeDetecter(),
            PhoneDetecter(),
        ]

    def run(self, frame) -> list[DetectionResult]:
        """
        주어진 frame에 대해 detecter들의 detect 결과를 반환한다.
        """
        return [d.detect(frame) for d in self._detectors]

class EyeDetecter(BaseDetector):
    def __init__(self):
        base_options = python.BaseOptions(model_asset_path='face_landmarker_v2_with_blendshapes.task')
        options = vision.FaceLandmarkerOptions(base_options=base_options,
                                            output_face_blendshapes=True,
                                            output_facial_transformation_matrixes=True,
                                            num_faces=1)
        self._detector = vision.FaceLandmarker.create_from_options(options)
        self.ear = 0.0

    def length(self, p1, p2):
        return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5

    def calculate_ear(self, landmarks, eye_indices):
        left = landmarks[eye_indices[0]]
        top_left = landmarks[eye_indices[1]]
        top_right = landmarks[eye_indices[2]]
        right = landmarks[eye_indices[3]]
        bottom_right = landmarks[eye_indices[4]]
        bottom_left = landmarks[eye_indices[5]]
        
        h_len = self.length(left, right)
        v_len = self.length(top_left, bottom_left) + self.length(top_right, bottom_right)

        return v_len / h_len

    def detect(self, frame) -> DetectionResult:
        """
        Take a frame and decide if the eyes are closed.
        """
        label = "eyes_opened"
        confidence = 1.0
        triggered = False
        metadata = {}

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)

        detection_result = self._detector.detect(image)
        if detection_result:
            landmarks = detection_result.face_landmarks[0]

            left_eye_indices = [362, 385, 387, 263, 373, 380]
            right_eye_indices = [33, 160, 158, 133, 153, 144]

            left_ear = self.calculate_ear(landmarks, left_eye_indices)
            right_ear = self.calculate_ear(landmarks, right_eye_indices)
            self.ear = (left_ear + right_ear) / 2.0

            if self.ear < EAR_THRESHOLD:
                label = "eyes_closed"
                triggered = True
                metadata["ear"] = self.ear

        return DetectionResult(label, confidence, triggered, metadata)


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
