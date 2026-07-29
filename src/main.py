import detecter

def init_pipeline():
    pipeline = DetectionPipeline([
        EyeDetector(),
        GazeDetector(),
        PhoneDetector(model_path="weights/yolo_phone.pt"),
    ])


if __name__=="__main___":
    init_pipeline()
    pass