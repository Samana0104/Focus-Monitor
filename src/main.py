from AI.detector import EyeDetecter, GazeDetecter, PhoneDetecter
import System

def init_pipeline():
    pipeline = System.pipeline.DetectionPipeline([
        EyeDetecter(),
        GazeDetecter(),
        PhoneDetecter(),
    ])


if __name__ == "__main__":
    init_pipeline()
