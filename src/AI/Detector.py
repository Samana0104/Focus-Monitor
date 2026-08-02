from abc import ABC, abstractmethod
from typing import Any, Sequence

from System.Define import DetectionResult, LogLevel

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2  

import numpy as np
import torch
import onnxruntime as ort
from Singleton.Settings import settings_instance
from System.FunctionLibrary import FunctionLibrary
from insightface.app import FaceAnalysis
from ultralytics import YOLO

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult:
        ...

class DetectionPipeline:
    def __init__(self) -> None:
        self._face_bbox: list[float] | None = None
        self._absence_detector = AbsenceDetecter()
        self._eye_detector = EyeDetecter()
        self._phone_detector = PhoneDetecter()

    def run(self, frame: np.ndarray) -> list[DetectionResult]:
        """
        주어진 frame에 대해 detecter들의 detect 결과를 반환한다.
        """
        absence_result = self._absence_detector.detect(frame)
        self._face_bbox = self._absence_detector.face_bbox      # Save bbox for later detection

        eye_result = self._eye_detector.detect(frame, self._face_bbox)
        phone_result = self._phone_detector.detect(frame, self._face_bbox)
        return [absence_result, eye_result, phone_result]

class EyeDetecter(BaseDetector):
    def __init__(self) -> None:
        model_path = FunctionLibrary.get_ai_path() / "face_landmarker_v2_with_blendshapes.task"
        base_options = python.BaseOptions(model_asset_path=str(model_path))
        options = vision.FaceLandmarkerOptions(base_options=base_options,
                                            output_face_blendshapes=True,
                                            output_facial_transformation_matrixes=True,
                                            num_faces=1)
        self._detector = vision.FaceLandmarker.create_from_options(options)

    def length(self, p1: Any, p2: Any) -> float:
        return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5

    def calculate_ear(self, landmarks: Sequence[Any], eye_indices: Sequence[int]) -> float:
        left = landmarks[eye_indices[0]]
        top_left = landmarks[eye_indices[1]]
        top_right = landmarks[eye_indices[2]]
        right = landmarks[eye_indices[3]]
        bottom_right = landmarks[eye_indices[4]]
        bottom_left = landmarks[eye_indices[5]]
        
        h_len = self.length(left, right)
        v_len = self.length(top_left, bottom_left) + self.length(top_right, bottom_right)

        return v_len / h_len

    def detect(self, frame: np.ndarray, face_bbox: Sequence[float] | None = None) -> DetectionResult:
        """
        Take a frame and decide if the eyes are closed.
        """
        label = "eyes_closed"
        triggered = False
        metadata = {"ear": 0.0, "eye_boxes": []}

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

            face_height, face_width = face_frame.shape[:2]
            for eye_indices in (left_eye_indices, right_eye_indices):
                eye_points = [(int(x1 + landmarks[index].x * face_width), int(y1 + landmarks[index].y * face_height)) for index in eye_indices]
                eye_x_values = [point[0] for point in eye_points]
                eye_y_values = [point[1] for point in eye_points]
                metadata["eye_boxes"].append([min(eye_x_values), min(eye_y_values), max(eye_x_values), max(eye_y_values)])

            if ear < float(settings_instance.ai_params["ear_threshold"]):
                triggered = True

        return DetectionResult(label, triggered, metadata)

class AbsenceDetecter(BaseDetector):
    def __init__(self) -> None:
        self._known_emb: np.ndarray | None = None
        self.face_bbox: list[float] | None = None
        self.face_embedding: np.ndarray | None = None
        available_providers = ort.get_available_providers()
        self._use_cuda = "CUDAExecutionProvider" in available_providers
        self._app = self.__create_face_analysis()

        FunctionLibrary.log(f"ONNX Runtime {ort.__version__} providers: {available_providers}")

    def __create_face_analysis(self) -> FaceAnalysis:
        if self._use_cuda:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            ctx_id = 0
        else:
            providers = ["CPUExecutionProvider"]
            ctx_id = -1

        try:
            app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"], providers=providers)
            app.prepare(ctx_id=ctx_id, det_size=(640, 640))

            sessions = (
                getattr(model, "session", None)
                for model in app.models.values()
            )
            self._use_cuda = any("CUDAExecutionProvider" in session.get_providers() for session in sessions if session is not None)
        except Exception as error:
            if not self._use_cuda:
                raise

            FunctionLibrary.log(f"InsightFace CUDA initialization failed; falling back to CPU: {error}", LogLevel.WARNING)
            self._use_cuda = False
            app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"], providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=-1, det_size=(640, 640))

        if self._use_cuda:
            device_name = "GPU (CUDA)"
        else:
            device_name = "CPU"
        FunctionLibrary.log(f"InsightFace device: {device_name}")
        return app

    def get_embedding(self, image: np.ndarray) -> tuple[bool, np.ndarray | None, list[float] | None]:
        """
        Gets the normlized embedding of the largest face found.
        """
        faces = self._app.get(image)
        
        if len(faces) == 0:
            return (False, None, None)

        faces.sort(
            key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]),
            reverse=True
        )

        face = faces[0]
        embedding = face.normed_embedding
        if embedding is None:
            return (False, None, None)

        bbox = face.bbox.tolist()
        return (True, embedding, bbox)


    def register_face(self, frame: np.ndarray) -> bool:
        """
        Register user face. 
        - returns True if succeeded
        """
        ret, embedding, _ = self.get_embedding(frame)
        if ret:
            self._known_emb = embedding.copy()

        return ret

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def detect(self, frame: np.ndarray) -> DetectionResult:
        label = "absent"
        triggered = True
        metadata = {"similarity": 0.0, "bbox": None}
        self.face_bbox = None
        
        ret, test_emb, bbox = self.get_embedding(frame)

        if ret and self._known_emb is not None:
            self.face_bbox = bbox
            metadata["bbox"] = bbox
            similarity = self.cosine_similarity(self._known_emb, test_emb)
            metadata["similarity"] = similarity
            if similarity > float(settings_instance.ai_params["similarity_threshold"]):
                triggered = False
            else:
                triggered = True
        elif ret:
            self.face_bbox = bbox
            metadata["bbox"] = bbox
            metadata["similarity"] = 1.0
            self._known_emb = test_emb.copy()
            triggered = False
            FunctionLibrary.log("Reference face registered automatically.")
        else:
            triggered = True

        return DetectionResult(label, triggered, metadata)

class PhoneDetecter(BaseDetector):
    def __init__(self) -> None:
        path: str = str(FunctionLibrary.get_ai_path() / "yolov11n.pt")
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            self._device = "cuda:0"
            device_name = "GPU (CUDA:0)"
        else:
            self._device = "cpu"
            device_name = "CPU"
        self._model = YOLO(path)
        FunctionLibrary.log(f"YOLO device: {device_name}")
        FunctionLibrary.log(f"PyTorch {torch.__version__}, CUDA build: {torch.version.cuda}, CUDA available: {cuda_available}")

    def detect(self, frame: np.ndarray, face_bbox: Sequence[float] | None = None) -> DetectionResult:
        label = "phone_detected"
        triggered = False
        metadata = {"confidence": 0.0, "norm_distance": 0.0, "boxes": []}

        if face_bbox is None:
            return DetectionResult(label, triggered, metadata)

        phone_confidence_threshold = float(settings_instance.ai_params.get("phone_confidence_threshold", 0.2))
        results = self._model.predict(
            frame,
            imgsz=640,
            classes=[int(settings_instance.ai_params["cell_phone_class"])],
            conf=phone_confidence_threshold,
            device=self._device,
            verbose=False,
        )

        face_x1, face_y1, face_x2, face_y2 = [float(value) for value in face_bbox]
        face_x = (face_x1 + face_x2) / 2.0
        face_y = (face_y1 + face_y2) / 2.0
        face_width = face_x2 - face_x1
        if face_width <= 0:
            return DetectionResult(label, triggered, metadata)

        closest_distance = None
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                if int(box.cls[0].item()) != int(settings_instance.ai_params["cell_phone_class"]):
                    continue

                phone_x1, phone_y1, phone_x2, phone_y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0].item())
                metadata["confidence"] = max(metadata["confidence"], confidence)
                metadata["boxes"].append({"bbox": [phone_x1, phone_y1, phone_x2, phone_y2], "confidence": confidence})
                phone_x = (phone_x1 + phone_x2) / 2.0
                phone_y = (phone_y1 + phone_y2) / 2.0
                distance = ((phone_x - face_x) ** 2 + (phone_y - face_y) ** 2) ** 0.5
                normalized_distance = distance / face_width

                if closest_distance is None or normalized_distance < closest_distance:
                    closest_distance = normalized_distance

        metadata["norm_distance"] = closest_distance
        if closest_distance is not None:
            triggered = closest_distance < float(settings_instance.ai_params["phone_face_distance_threshold"])

        return DetectionResult(label, triggered, metadata)
