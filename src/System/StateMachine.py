"""Simple concentration state machine for one study session."""

from datetime import datetime, timedelta, timezone
from enum import Enum

from System.Define import LogLevel
from System.FunctionLibrary import FunctionLibrary


class FocusState(Enum):
    FOCUSED = "focused"
    PHONE = "phone"
    DROWSY = "drowsy"
    ABSENT = "absent"


class AlertLevel(Enum):
    NONE = 0
    WARNING = 1
    ALERT = 2


class StateInterval:
    def __init__(self, state, started_at):
        self.state = state
        self.started_at = started_at
        self.ended_at = None


class FocusReport:
    def __init__(self, started_at, ended_at, durations, focus_ratio, timeline):
        self.session_started_at = started_at
        self.session_ended_at = ended_at
        self.total_duration = ended_at - started_at
        self.duration_by_state = durations
        self.focus_ratio = focus_ratio
        self.timeline = timeline

        self.distraction_count = 0
        self.drowsiness_count = 0
        for interval in timeline:
            if interval.state != FocusState.FOCUSED:
                self.distraction_count += 1
            if interval.state == FocusState.DROWSY:
                self.drowsiness_count += 1


class FocusStateMachine:
    """
    State priority: ABSENT > DROWSY > PHONE > FOCUSED.
    The caller should call ``update(results, timestamp)`` once per frame.
    """
    DEFAULT_ENTER_SECONDS = {
        FocusState.ABSENT: 3,
        FocusState.DROWSY: 3,
        FocusState.PHONE: 2,
    }
    DEFAULT_EXIT_SECONDS = {
        FocusState.ABSENT: 1,
        FocusState.DROWSY: 1,
        FocusState.PHONE: 1,
    }

    def __init__(self):
        self.enter_seconds = self.DEFAULT_ENTER_SECONDS.copy()
        self.exit_seconds = self.DEFAULT_EXIT_SECONDS.copy()
        self.warning_seconds = 5
        self.alert_seconds = 15
        self.reset()

    def start_session(self, started_at=None):
        """
        Start a new session.
        """
        if started_at is None:
            started_at = datetime.now(timezone.utc)
        self.reset()
        self.session_started_at = started_at
        self.last_timestamp = started_at
        self.timeline.append(StateInterval(FocusState.FOCUSED, started_at))

    def update(self, results, timestamp=None):
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

        observed_state = self._choose_state(results)
        if observed_state == self.state:
            # discard candidate if current state maintains.
            self.candidate_state = None
            self.candidate_started_at = None
        else:
            if observed_state != self.candidate_state:
                # override candidate
                self.candidate_state = observed_state
                self.candidate_started_at = timestamp

            if observed_state == FocusState.FOCUSED:
                needed_seconds = self.exit_seconds.get(self.state, 0)
            else:
                needed_seconds = self.enter_seconds.get(observed_state, 0)

            passed_seconds = (timestamp - self.candidate_started_at).total_seconds()
            if passed_seconds >= needed_seconds:
                # promote candidate to new state
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

    def end_session(self, ended_at=None):
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
        durations = {}      # accumulative durations for each state
        for state in FocusState:
            durations[state] = timedelta()
        for interval in self.timeline:
            durations[interval.state] += interval.ended_at - interval.started_at

        total_duration = ended_at - self.session_started_at
        if total_duration > timedelta():
            focus_ratio = durations[FocusState.FOCUSED] / total_duration
        else:
            focus_ratio = 0.0
        return FocusReport(
            self.session_started_at, ended_at, durations, focus_ratio, list(self.timeline)
        )

    def reset(self):
        """
        Reset session.
        """
        self.state = FocusState.FOCUSED
        self.alert_level = AlertLevel.NONE
        self.session_started_at = None
        self.last_timestamp = None
        self.candidate_state = None
        self.candidate_started_at = None
        self.timeline = []

    def _choose_state(self, results):
        """
        Choose a single state that best represents the detection results.
        """
        labels = []
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

    def _change_state(self, next_state, timestamp):
        """
        Close the current interval and start a new one with a different state.
        """
        previous_state = self.state
        self._close_interval(timestamp)
        self.state = next_state
        self.timeline.append(StateInterval(next_state, timestamp))
        self.candidate_state = None
        self.candidate_started_at = None

        FunctionLibrary.log(
            f"STATE_CHANGED {previous_state.name}->{next_state.name}",
            LogLevel.NONE,
        )

    def _close_interval(self, timestamp):
        if self.timeline and self.timeline[-1].ended_at is None:
            self.timeline[-1].ended_at = timestamp
