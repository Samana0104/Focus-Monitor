from abc import ABC, abstractmethod
from System.Define import (
    DetectionResult,
    EAR_THRESHOLD,
    SIMILARITY_THRESHOLD,
    PHONE_FACE_DISTANCE_THRESHOLD,
)

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2  
from pathlib import Path

import numpy as np
from insightface.app import FaceAnalysis

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, frame) -> DetectionResult:
        ...

class DetectionPipeline:
    def __init__(self):
        self._face_bbox = None
        self._absence_detector = AbsenceDetecter()
        self._eye_detector = EyeDetecter()
        self._phone_detector = PhoneDetecter()

    def run(self, frame) -> list[DetectionResult]:
        """
        주어진 frame에 대해 detecter들의 detect 결과를 반환한다.
        """
        absence_result = self._absence_detector.detect(frame)
        self._face_bbox = self._absence_detector.face_bbox      # Save bbox for later detection

        eye_result = self._eye_detector.detect(frame, self._face_bbox)
        phone_result = self._phone_detector.detect(frame, self._face_bbox)
        return [absence_result, eye_result, phone_result]

class EyeDetecter(BaseDetector):
    def __init__(self):
        model_path = str(Path(__file__).parent / "face_landmarker_v2_with_blendshapes.task")
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(base_options=base_options,
                                            output_face_blendshapes=True,
                                            output_facial_transformation_matrixes=True,
                                            num_faces=1)
        self._detector = vision.FaceLandmarker.create_from_options(options)

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

    def detect(self, frame, face_bbox=None) -> DetectionResult:
        """
        Take a frame and decide if the eyes are closed.
        """
        label = "eyes_closed"
        triggered = False
        metadata = {"ear": 0.0}

        if face_bbox is None:
            return DetectionResult(label, triggered, metadata)

        x1, y1, x2, y2 = [int(value) for value in face_bbox]
        frame_height, frame_width = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(frame_width, x2)
        y2 = min(frame_height, y2)
        face_frame = frame[y1:y2, x1:x2]        # crop face
        if face_frame.size == 0:
            return DetectionResult(label, triggered, metadata)

        img = cv2.cvtColor(face_frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)

        detection_result = self._detector.detect(image)
        if detection_result.face_landmarks:
            landmarks = detection_result.face_landmarks[0]

            left_eye_indices = [362, 385, 387, 263, 373, 380]
            right_eye_indices = [33, 160, 158, 133, 153, 144]

            left_ear = self.calculate_ear(landmarks, left_eye_indices)
            right_ear = self.calculate_ear(landmarks, right_eye_indices)
            ear = (left_ear + right_ear) / 2.0
            metadata["ear"] = ear

            if ear < EAR_THRESHOLD:
                triggered = True

        return DetectionResult(label, triggered, metadata)

class AbsenceDetecter(BaseDetector):
    def __init__(self):
        self._known_emb = None
        self.face_bbox = None
        self.face_embedding = None
        # Load InsightFace Model
        self._app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )
        self._app.prepare(
            ctx_id=0,
            det_size=(640, 640)
        )

    def get_embedding(self, image) -> tuple[bool, np.ndarray, list]:
        """
        Gets the normlized embedding of the largest face found.
        """
        faces = self._app(image)
        
        if len(faces) == 0:
            return (False, None, None)

        faces.sort(
            key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]),
            reverse=True
        )

        face = faces[0]
        embedding = face.embedding
        bbox = face.bbox.tolist()
        return (True, embedding / np.linalg.norm(embedding), bbox)


    def register_face(self, frame) -> bool:
        """
        Register user face. 
        - returns True if succeeded
        """
        cvt_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ret, embedding, _ = self.get_embedding(cvt_image)
        if ret:
            self._known_emb = embedding

        return ret

    def cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def detect(self, frame) -> DetectionResult:
        label = "absent"
        triggered = True
        metadata = {"similarity": 0.0}
        self.face_bbox = None
        
        cvt_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ret, test_emb, bbox = self.get_embedding(cvt_image)
        if ret and self._known_emb is not None:
            self.face_bbox = bbox
            similarity = self.cosine_similarity(self._known_emb, test_emb)
            metadata["similarity"] = similarity
            if similarity > SIMILARITY_THRESHOLD:
                triggered = False
            else:
                triggered = True
        elif ret:
            self.face_bbox = bbox
        else:
            triggered = True

        return DetectionResult(label, triggered, metadata)

        

class PhoneDetecter(BaseDetector):
    def __init__(self):
        pass

    def detect(self, frame) -> DetectionResult:
        pass
