import cv2

class CameraWorker():

    def __init__(self, pipeline, state_machine):
        super().__init__()
        self._pipeline = pipeline
        self._sm       = state_machine

    def run(self):
        """
        Run the detection pipeline and update the state machine.
        """
        cap = cv2.VideoCapture(0)
        while self._running:
            ret, frame = cap.read()

            # TODO :
            # pipeline run
            # update state machine
            # publish results on eventbus

            pass
