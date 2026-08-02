"""Simple concentration state machine for one study session."""

from datetime import datetime, timedelta, timezone

from Singleton.Events import event_manager
from Singleton.Settings import settings_instance
from System.Define import AlertLevel, DetectionResult, EventKey, FocusState, LogLevel
from System.FunctionLibrary import FunctionLibrary


class StateInterval:
    def __init__(self, state: FocusState, started_at: datetime) -> None:
        self.state: FocusState = state
        self.started_at: datetime = started_at
        self.ended_at: datetime | None = None


class FocusReport:
    def __init__(self, started_at: datetime, ended_at: datetime, durations: dict[FocusState, timedelta], focus_ratio: float, timeline: list[StateInterval]) -> None:
        self.session_started_at: datetime = started_at
        self.session_ended_at: datetime = ended_at
        self.total_duration: timedelta = ended_at - started_at
        self.duration_by_state: dict[FocusState, timedelta] = durations
        self.focus_ratio: float = focus_ratio
        self.timeline: list[StateInterval] = timeline

        self.distraction_count: int = 0
        self.drowsiness_count: int = 0
        for interval in timeline:
            if interval.state != FocusState.FOCUSED:
                self.distraction_count += 1
            if interval.state == FocusState.DROWSY:
                self.drowsiness_count += 1


class FocusStateMachine:
    """
    State priority: ABSENT > DROWSY > PHONE > FOCUSED.
    State entry and release use separate duration thresholds.
    """

    def __init__(self) -> None:
        self.enter_seconds: dict[FocusState, float] = {}
        self.release_seconds: dict[FocusState, float] = {}
        self.warning_seconds: float = 5.0
        self.alert_seconds: float = 15.0
        self.reset()

    def start_session(self, started_at: datetime | None = None) -> None:
        """
        Start a new session.
        """
        if started_at is None:
            started_at = datetime.now(timezone.utc)
        self.reset()
        self.session_started_at = started_at
        self.last_timestamp = started_at
        self.timeline.append(StateInterval(FocusState.FOCUSED, started_at))

    def update(self, results: list[DetectionResult], timestamp: datetime | None = None) -> FocusState:
        """
        Try and update the state by every frame.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        if self.session_started_at is None:
            self.start_session(timestamp)
        if timestamp < self.last_timestamp:
            raise ValueError("timestamps must be in chronological order")
        self.last_timestamp = timestamp
        self.__load_state_seconds()

        observed_state: FocusState = self._choose_state(results)
        if observed_state == self.state:
            self.__reset_transition()
        else:
            self.__update_transition(observed_state, timestamp)
            if self.__can_change_state(observed_state, timestamp):
                self._change_state(observed_state, timestamp)

        if self.state != FocusState.FOCUSED:
            lasting_seconds = (timestamp - self.timeline[-1].started_at).total_seconds()
            next_alert = AlertLevel.NONE
            if lasting_seconds >= self.alert_seconds:
                next_alert = AlertLevel.ALERT
            elif lasting_seconds >= self.warning_seconds:
                next_alert = AlertLevel.WARNING

            if next_alert != self.alert_level:
                self.alert_level = next_alert
                if next_alert == AlertLevel.WARNING:
                    FunctionLibrary.log(f"{self.state.name}_WARNING", LogLevel.WARNING)
                elif next_alert == AlertLevel.ALERT:
                    FunctionLibrary.log(f"{self.state.name}_ALERT", LogLevel.DANGER)
        else:
            self.alert_level = AlertLevel.NONE

        return self.state

    def end_session(self, ended_at: datetime | None = None) -> FocusReport:
        """
        End the current session.
        """
        if self.session_started_at is None:
            raise RuntimeError("cannot end a session that has not started")
        if ended_at is None:
            ended_at = datetime.now(timezone.utc)
        if ended_at < self.last_timestamp:
            raise ValueError("end time cannot be earlier than the latest update")

        self._close_interval(ended_at)
        self.last_timestamp = ended_at
        durations: dict[FocusState, timedelta] = {}
        for state in FocusState:
            durations[state] = timedelta()
        for interval in self.timeline:
            if interval.ended_at is not None:
                durations[interval.state] += interval.ended_at - interval.started_at

        total_duration: timedelta = ended_at - self.session_started_at
        if total_duration > timedelta():
            focus_ratio: float = durations[FocusState.FOCUSED] / total_duration
        else:
            focus_ratio = 0.0
        return FocusReport(self.session_started_at, ended_at, durations, focus_ratio, list(self.timeline))

    def reset(self) -> None:
        """
        Reset session.
        """
        self.state: FocusState = FocusState.FOCUSED
        self.alert_level: AlertLevel = AlertLevel.NONE
        self.session_started_at: datetime | None = None
        self.last_timestamp: datetime | None = None
        self.state_mismatch_started_at: datetime | None = None
        self.candidate_state: FocusState | None = None
        self.candidate_started_at: datetime | None = None
        self.timeline: list[StateInterval] = []

    def _choose_state(self, results: list[DetectionResult]) -> FocusState:
        """
        Choose a single state that best represents the detection results.
        """
        labels: list[str] = []
        for result in results:
            if result.triggered:
                labels.append(result.label)

        if "absent" in labels:
            return FocusState.ABSENT
        if "eyes_closed" in labels:
            return FocusState.DROWSY
        if "phone_detected" in labels:
            return FocusState.PHONE
        return FocusState.FOCUSED

    def _change_state(self, next_state: FocusState, timestamp: datetime) -> None:
        """
        Close the current interval and start a new one with a different state.
        """
        previous_state: FocusState = self.state
        self._close_interval(timestamp)
        self.state = next_state
        self.timeline.append(StateInterval(next_state, timestamp))
        self.__reset_transition()

        FunctionLibrary.log(f"STATE_CHANGED {previous_state.name}->{next_state.name}", LogLevel.NONE)
        self.__publish_state_event(previous_state, next_state)

    def __load_state_seconds(self) -> None:
        self.enter_seconds = {
            FocusState.ABSENT: max(0.0, float(settings_instance.ai_params.get("absence_enter_seconds", 3.0))),
            FocusState.DROWSY: max(0.0, float(settings_instance.ai_params.get("drowsy_enter_seconds", 3.0))),
            FocusState.PHONE: max(0.0, float(settings_instance.ai_params.get("phone_enter_seconds", 2.0))),
        }
        self.release_seconds = {
            FocusState.ABSENT: max(0.0, float(settings_instance.ai_params.get("absence_release_seconds", 3.0))),
            FocusState.DROWSY: max(0.0, float(settings_instance.ai_params.get("drowsy_release_seconds", 3.0))),
            FocusState.PHONE: max(0.0, float(settings_instance.ai_params.get("phone_release_seconds", 3.0))),
        }

    def __update_transition(self, observed_state: FocusState, timestamp: datetime) -> None:
        if self.state_mismatch_started_at is None:
            self.state_mismatch_started_at = timestamp

        if observed_state != self.candidate_state:
            self.candidate_state = observed_state
            self.candidate_started_at = timestamp

    def __can_change_state(self, observed_state: FocusState, timestamp: datetime) -> bool:
        if self.state_mismatch_started_at is None or self.candidate_started_at is None:
            return False

        mismatch_seconds: float = (timestamp - self.state_mismatch_started_at).total_seconds()
        candidate_seconds: float = (timestamp - self.candidate_started_at).total_seconds()
        if self.state == FocusState.FOCUSED:
            return candidate_seconds >= self.enter_seconds[observed_state]

        if mismatch_seconds < self.release_seconds[self.state]:
            return False

        if observed_state == FocusState.FOCUSED:
            return True

        return candidate_seconds >= self.enter_seconds[observed_state]

    def __reset_transition(self) -> None:
        self.state_mismatch_started_at = None
        self.candidate_state = None
        self.candidate_started_at = None

    def __publish_state_event(self, previous_state: FocusState, next_state: FocusState) -> None:
        if next_state == FocusState.ABSENT:
            event_key = EventKey.ABSENCE_DETECTED
        elif next_state == FocusState.DROWSY:
            event_key = EventKey.DROWSY_DETECTED
        elif next_state == FocusState.PHONE:
            event_key = EventKey.PHONE_DETECTED
        elif previous_state != FocusState.FOCUSED:
            event_key = EventKey.ALERT_CLEARED
        else:
            return

        event_manager.publish(event_key.value, state=next_state)

    def _close_interval(self, timestamp: datetime) -> None:
        if self.timeline and self.timeline[-1].ended_at is None:
            self.timeline[-1].ended_at = timestamp
