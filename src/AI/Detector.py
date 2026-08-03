from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence
import numpy as np
import torch
import cv2
import onnxruntime as ort

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from insightface.app import FaceAnalysis
from ultralytics import YOLO
from ultralytics.engine.results import Results

from System.Define import DetectionResult, LogLevel
from Singleton.Settings import settings_instance
from System.FunctionLibrary import FunctionLibrary

@dataclass
class FrameContext:
    """
    For sharing common data in processing a single frame.
    """
    frame: np.ndarray
    yolo_results: Optional[List[Results]] = None
    face_bbox: Optional[List[float]] = None


class GlobalEngines:
    """
    Load the models only once.
    """
    _face_landmarker: Optional[vision.FaceLandmarker] = None    # Mediapipe
    _face_analysis: Optional[FaceAnalysis] = None               # InsightFace
    _yolo_model: Optional[YOLO] = None                          # Ultralytics/YOLO
    _yolo_device: str = "cpu"                   # default is CPU.

    @classmethod
    def get_face_landmarker(cls) -> vision.FaceLandmarker:
        if cls._face_landmarker is None:
            model_path = FunctionLibrary.get_ai_path() / "face_landmarker_v2_with_blendshapes.task"
            base_options = python.BaseOptions(model_asset_path=str(model_path))
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                num_faces=1,
            )
            cls._face_landmarker = vision.FaceLandmarker.create_from_options(options)
            FunctionLibrary.log("Global FaceLandmarker engine initialized.")
        return cls._face_landmarker

    @classmethod
    def get_face_analysis(cls) -> FaceAnalysis:
        if cls._face_analysis is None:
            available_providers = ort.get_available_providers()
            use_cuda = "CUDAExecutionProvider" in available_providers       # Use GPU if possible
            FunctionLibrary.log(f"ONNX Runtime {ort.__version__} providers: {available_providers}")

            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_cuda else ["CPUExecutionProvider"]
            ctx_id = 0 if use_cuda else -1

            try:
                app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"], providers=providers)
                app.prepare(ctx_id=ctx_id, det_size=(640, 640))

                sessions = (getattr(model, "session", None) for model in app.models.values())
                use_cuda = any("CUDAExecutionProvider" in session.get_providers() for session in sessions if session is not None)
            except Exception as error:
                if not use_cuda:
                    raise
                FunctionLibrary.log(f"InsightFace CUDA init failed; falling back to CPU: {error}", LogLevel.WARNING)
                use_cuda = False
                app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"], providers=["CPUExecutionProvider"])
                app.prepare(ctx_id=-1, det_size=(640, 640))

            device_name = "GPU (CUDA)" if use_cuda else "CPU"
            FunctionLibrary.log(f"InsightFace device: {device_name}")
            cls._face_analysis = app

        return cls._face_analysis

    @classmethod
    def get_yolo_model(cls) -> tuple[YOLO, str]:
        if cls._yolo_model is None:
            path = str(FunctionLibrary.get_ai_path() / "yolov11n.pt")
            cuda_available = torch.cuda.is_available()
            cls._yolo_device = "cuda:0" if cuda_available else "cpu"        # Use GPU if possible
            device_name = "GPU (CUDA:0)" if cuda_available else "CPU"

            cls._yolo_model = YOLO(path)
            FunctionLibrary.log(f"YOLO device: {device_name}")
            FunctionLibrary.log(f"PyTorch {torch.__version__}, CUDA build: {torch.version.cuda}, CUDA available: {cuda_available}")

        return cls._yolo_model, cls._yolo_device

# =========================
# detectors
# =========================

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult:
        ...

class DetectionPipeline:
    def __init__(self) -> None:
        self._absence_detector = AbsenceDetector()
        self._eye_detector = EyeDetector()
        self._phone_detector = PhoneDetector()

    def run(self, frame: np.ndarray) -> list[DetectionResult]:
        """
        Infer once and share results with Detectors via FrameContext.
        """
        # Get yolo model and detect both person and phone
        yolo_model, device = GlobalEngines.get_yolo_model()
        person_class = int(settings_instance.ai_params.get("person_class"))
        phone_class = int(settings_instance.ai_params.get("cell_phone_class"))
        phone_conf_thresh = float(settings_instance.ai_params.get("phone_confidence_threshold"))

        shared_yolo_results = yolo_model.predict(
            frame,
            imgsz=640,
            classes=[person_class, phone_class],
            conf=phone_conf_thresh,
            device=device,
            verbose=False,
        )

        # Create FrameContext
        context = FrameContext(
            frame=frame,
            yolo_results=shared_yolo_results
        )

        # Detect absence and save detected face bbox
        absence_result = self._absence_detector.detect(context)
        context.face_bbox = self._absence_detector.face_bbox

        # Detect eye closedness and phone use
        eye_result = self._eye_detector.detect(context)
        phone_result = self._phone_detector.detect(context)

        return [absence_result, eye_result, phone_result]

class AbsenceDetector(BaseDetector):
    def __init__(self) -> None:
        self._known_emb: np.ndarray | None = None
        self.face_bbox: list[float] | None = None
        self._last_known_bbox: list[float] | None = None

    @property
    def _app(self) -> FaceAnalysis:
        return GlobalEngines.get_face_analysis()

    def get_embedding(self, image: np.ndarray) -> tuple[bool, np.ndarray | None, list[float] | None]:
        """ Get embedding of the largest detected face in the frame. """
        faces = self._app.get(image)
        if len(faces) == 0:
            return (False, None, None)

        faces.sort(
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            reverse=True,
        )

        face = faces[0]
        embedding = face.normed_embedding
        if embedding is None:
            return (False, None, None)

        bbox = face.bbox.tolist()
        return (True, embedding, bbox)

    def register_face(self, frame: np.ndarray) -> bool:
        ret, embedding, bbox = self.get_embedding(frame)
        if ret and embedding is not None:
            self._known_emb = embedding.copy()
            self._last_known_bbox = bbox
        return ret

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def _is_person_near_last_bbox(self, yolo_results: Optional[List[Results]], person_class: int) -> bool:
        """YOLO 감지 BBox가 마지막으로 확인된 얼굴 위치 근처(ROI)에 존재하는지 확인"""
        if not yolo_results or self._last_known_bbox is None:
            return False

        fx1, fy1, fx2, fy2 = self._last_known_bbox
        face_cx = (fx1 + fx2) / 2.0
        face_cy = (fy1 + fy2) / 2.0
        face_w = fx2 - fx1
        face_area = (fx2 - fx1) * (fy2 - fy1)

        # Region of interest : trifold of face width
        threshold_dist = max(face_w * 3.0, 150.0)

        for result in yolo_results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                if int(box.cls[0].item()) == person_class:
                    px1, py1, px2, py2 = box.xyxy[0].tolist()
                    person_cx = (px1 + px2) / 2.0
                    person_area = (px2 - px1) * (py2 - py1)
                    
                    # Check whether person exists in ROI
                    dist = ((person_cx - face_cx) ** 2 + (py1 - face_cy) ** 2) ** 0.5

                    # If person is close enough to face & person is 
                    if dist <= threshold_dist and person_area >= face_area:
                        return True
        return False

    def detect(self, context: FrameContext) -> DetectionResult:
        label = "absent"
        triggered = True
        metadata = {"similarity": 0.0, "bbox": None}
        self.face_bbox = None

        person_class = int(settings_instance.ai_params.get("person_class", 0))

        # -------------------------------------------------------------
        # 1차 검증: InsightFace를 통한 얼굴 감지 및 유사도 비교
        # -------------------------------------------------------------
        ret, test_emb, bbox = self.get_embedding(context.frame)

        if ret and test_emb is not None:
            if self._known_emb is not None:
                similarity = self.cosine_similarity(self._known_emb, test_emb)
                metadata["similarity"] = similarity
                
                if similarity > float(settings_instance.ai_params["similarity_threshold"]):
                    triggered = False
                    self.face_bbox = bbox
                    self._last_known_bbox = bbox
                    metadata["bbox"] = bbox
                    return DetectionResult(label, triggered, metadata)
            else:
                # 최초 1회 등록
                self._known_emb = test_emb.copy()
                self._last_known_bbox = bbox
                self.face_bbox = bbox
                metadata["bbox"] = bbox
                metadata["similarity"] = 1.0
                triggered = False
                FunctionLibrary.log("Reference face registered automatically.")
                return DetectionResult(label, triggered, metadata)

        # -------------------------------------------------------------
        # 2차 검증: InsightFace 미감지 시 (필기 등으로 고개 숙임), 
        #           마지막 확인 위치 기준 YOLO 'person' 존재 여부 확인
        # -------------------------------------------------------------
        if self._is_person_near_last_bbox(context.yolo_results, person_class):
            triggered = False
            # 기존 face_bbox는 연관성 저하 예방을 위해 None으로 유지하여
            # EyeDetector 등의 오작동을 방지함.

        return DetectionResult(label, triggered, metadata)


class EyeDetector(BaseDetector):
    def __init__(self) -> None:
        pass

    @property
    def _detector(self) -> vision.FaceLandmarker:
        return GlobalEngines.get_face_landmarker()

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

        return v_len / h_len if h_len > 0 else 0.0

    def detect(self, context: FrameContext) -> DetectionResult:
        label = "eyes_closed"
        triggered = False
        metadata = {"ear": 0.0, "eye_boxes": []}

        if context.face_bbox is None:
            return DetectionResult(label, triggered, metadata)

        x1, y1, x2, y2 = [int(value) for value in context.face_bbox]
        frame_height, frame_width = context.frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(frame_width, x2)
        y2 = min(frame_height, y2)
        face_frame = context.frame[y1:y2, x1:x2]

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
                eye_points = [(int(x1 + landmarks[idx].x * face_width), int(y1 + landmarks[idx].y * face_height)) for idx in eye_indices]
                eye_x_values = [p[0] for p in eye_points]
                eye_y_values = [p[1] for p in eye_points]
                metadata["eye_boxes"].append([min(eye_x_values), min(eye_y_values), max(eye_x_values), max(eye_y_values)])

            if ear < float(settings_instance.ai_params["ear_threshold"]):
                triggered = True

        return DetectionResult(label, triggered, metadata)


class PhoneDetector(BaseDetector):
    def __init__(self) -> None:
        pass

    def detect(self, context: FrameContext) -> DetectionResult:
        label = "phone_detected"
        triggered = False
        metadata = {"confidence": 0.0, "norm_distance": 0.0, "boxes": []}

        if context.face_bbox is None or context.yolo_results is None:
            return DetectionResult(label, triggered, metadata)

        cell_phone_class = int(settings_instance.ai_params["cell_phone_class"])
        face_x1, face_y1, face_x2, face_y2 = [float(value) for value in context.face_bbox]
        face_x = (face_x1 + face_x2) / 2.0
        face_y = (face_y1 + face_y2) / 2.0
        face_width = face_x2 - face_x1
        if face_width <= 0:
            return DetectionResult(label, triggered, metadata)

        closest_distance = None

        # 파이프라인에서 전달받은 shared_yolo_results 재사용
        for result in context.yolo_results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                if int(box.cls[0].item()) != cell_phone_class:
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