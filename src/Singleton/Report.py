from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from Singleton.Singleton import Singleton

if TYPE_CHECKING:
    from System.Define import FocusState


STATE_INFO: dict[str, tuple[str, str]] = {
    "focused": ("집중", "focused"),
    "break": ("휴식", "break"),
    "phone": ("휴대폰", "phone"),
    "drowsy": ("졸음", "drowsy"),
    "absent": ("자리 비움", "absent"),
}

class ReportManager(Singleton):
    """Keep a parameter-free timeline of focus states for the current session."""

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._lock = Lock()
        self._started_at = datetime.now().astimezone()
        self._last_seen_at: datetime | None = None
        self._intervals: list[dict[str, Any]] = []
        self._events_subscribed = False

    def initialize(self) -> None:
        if self._events_subscribed:
            return

        from Singleton.Events import event_manager

        event_manager.subscribe("START_REQUESTED", self._on_start_requested)
        event_manager.subscribe("BREAK_REQUESTED", self._on_break_requested)
        self._events_subscribed = True

    def shutdown(self) -> None:
        if not self._events_subscribed:
            return

        from Singleton.Events import event_manager

        event_manager.unsubscribe("START_REQUESTED", self._on_start_requested)
        event_manager.unsubscribe("BREAK_REQUESTED", self._on_break_requested)
        self._events_subscribed = False

    @property
    def record_count(self) -> int:
        with self._lock:
            return len(self._intervals)

    def clear(self) -> None:
        """Start a new in-memory schedule."""
        with self._lock:
            self._started_at = datetime.now().astimezone()
            self._last_seen_at = None
            self._intervals.clear()

    def record_state(self, state: FocusState, timestamp: datetime | None = None) -> None:
        """Merge consecutive samples of the same focus state into one interval."""
        self._record_state_value(str(state.value), timestamp)

    def _on_start_requested(self, payload: dict[str, Any]) -> None:
        self._record_state_value("focused")

    def _on_break_requested(self, payload: dict[str, Any]) -> None:
        self._record_state_value("break")

    def _record_state_value(self, state_value: str, timestamp: datetime | None = None) -> None:
        observed_at = timestamp or datetime.now().astimezone()
        if observed_at.tzinfo is None:
            observed_at = observed_at.astimezone()

        with self._lock:
            if self._last_seen_at is not None and observed_at < self._last_seen_at:
                return

            if self._intervals and self._intervals[-1]["state"] == state_value:
                self._intervals[-1]["ended_at"] = observed_at
            else:
                if self._intervals:
                    self._intervals[-1]["ended_at"] = observed_at
                interval = {
                    "state": state_value,
                    "started_at": observed_at if self._intervals else self._started_at,
                    "ended_at": observed_at,
                }
                self._intervals.append(interval)
            self._last_seen_at = observed_at

    def export_html(self, output_path: Path | None = None) -> Path:
        """Write a standalone dark-theme schedule and return its absolute path."""
        from System.FunctionLibrary import FunctionLibrary

        with self._lock:
            started_at = self._started_at
            intervals = [dict(interval) for interval in self._intervals]

        generated_at = datetime.now().astimezone()
        if intervals:
            intervals[-1]["ended_at"] = generated_at
        if output_path is None:
            report_dir = FunctionLibrary.get_root_path() / "reports"
            output_path = report_dir / f"schedule_{generated_at:%Y%m%d_%H%M%S}.html"

        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self._build_html(intervals, started_at, generated_at), encoding="utf-8")
        return output_path

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total = max(0, round(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}시간 {minutes}분 {secs}초"
        if minutes:
            return f"{minutes}분 {secs}초"
        return f"{secs}초"

    @staticmethod
    def _build_html(intervals: list[dict[str, Any]], started_at: datetime, generated_at: datetime) -> str:
        durations: defaultdict[str, float] = defaultdict(float)
        for interval in intervals:
            durations[interval["state"]] += max(0.0, (interval["ended_at"] - interval["started_at"]).total_seconds())

        total_seconds = sum(durations.values())
        focused_seconds = durations["focused"]
        focus_ratio = focused_seconds / total_seconds * 100 if total_seconds else 0.0

        summary_parts = [
            f'<div class="metric {css_class}"><span>{escape(title)}</span>'
            f"<strong>{ReportManager._format_duration(durations[state])}</strong></div>"
            for state, (title, css_class) in STATE_INFO.items()
        ]
        summary_cards = "".join(summary_parts)

        timeline_parts = [
            f'<div class="segment {STATE_INFO.get(interval["state"], (interval["state"], "focused"))[1]}" '
            f'style="width:{max(0.8, (interval["ended_at"] - interval["started_at"]).total_seconds() / total_seconds * 100) if total_seconds else 100:.2f}%" '
            f'title="{escape(STATE_INFO.get(interval["state"], (interval["state"], ""))[0])}: '
            f'{interval["started_at"]:%H:%M:%S} - {interval["ended_at"]:%H:%M:%S}"></div>'
            for interval in intervals
        ]
        timeline_segments = "".join(timeline_parts) or '<div class="empty-bar">아직 기록된 일정이 없습니다.</div>'

        schedule_parts = [
            "<tr>"
            f"<td>{interval['started_at']:%H:%M:%S}</td>"
            f"<td>{interval['ended_at']:%H:%M:%S}</td>"
            f'<td><span class="badge {STATE_INFO.get(interval["state"], ("", "focused"))[1]}">'
            f'{escape(STATE_INFO.get(interval["state"], (interval["state"], ""))[0])}</span></td>'
            f"<td>{ReportManager._format_duration((interval['ended_at'] - interval['started_at']).total_seconds())}</td>"
            "</tr>"
            for interval in intervals
        ]
        schedule_rows = "".join(schedule_parts) or '<tr><td colspan="4" class="empty">아직 기록된 일정이 없습니다.</td></tr>'

        observed_end = intervals[-1]["ended_at"] if intervals else started_at
        return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>집중 일정 리포트</title>
<style>
:root{{--bg:#090d16;--panel:#111827;--line:#263244;--text:#f4f7fb;--muted:#9aa8bc;--focus:#43d39e;--break:#38bdf8;--phone:#ffb547;--drowsy:#a78bfa;--absent:#ff6b7a}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at top,#172033 0,var(--bg) 48%);color:var(--text);font-family:Segoe UI,Apple SD Gothic Neo,sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:48px 24px 72px}} h1{{font-size:34px;margin:0 0 8px}} h2{{margin:0 0 18px;font-size:19px}}
.sub{{color:var(--muted);line-height:1.7;margin-bottom:28px}} .panel{{background:#111827e8;border:1px solid var(--line);border-radius:18px;padding:22px;margin:18px 0;box-shadow:0 18px 50px #0006}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}} .metric{{background:#0c1320;border:1px solid var(--line);border-top:3px solid;padding:16px;border-radius:12px}}
.metric span{{display:block;color:var(--muted);font-size:13px;margin-bottom:8px}} .metric strong{{font-size:18px}} .focused{{border-color:var(--focus)!important}} .break{{border-color:var(--break)!important}} .phone{{border-color:var(--phone)!important}} .drowsy{{border-color:var(--drowsy)!important}} .absent{{border-color:var(--absent)!important}}
.headline{{display:flex;justify-content:space-between;align-items:end;gap:16px}} .ratio{{font-size:30px;font-weight:750;color:var(--focus)}}
.timeline{{display:flex;min-height:54px;overflow:hidden;background:#080c14;border:1px solid var(--line);border-radius:12px;margin-top:18px}} .segment{{min-width:3px;border:0;border-right:1px solid #08101b}}
.segment.focused{{background:var(--focus)}} .segment.break{{background:var(--break)}} .segment.phone{{background:var(--phone)}} .segment.drowsy{{background:var(--drowsy)}} .segment.absent{{background:var(--absent)}}
.axis{{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;margin-top:8px}} .empty-bar{{padding:17px;color:var(--muted)}}
.table-wrap{{overflow-x:auto}} table{{width:100%;border-collapse:collapse}} th,td{{padding:13px 14px;text-align:left;border-bottom:1px solid var(--line)}} th{{color:var(--muted);font-size:12px;text-transform:uppercase}} td{{color:#e7edf7}}
.badge{{display:inline-block;border:1px solid;border-radius:999px;padding:5px 11px;background:#ffffff08;font-weight:650}} .empty{{text-align:center;color:var(--muted)}}
@media(max-width:720px){{.metrics{{grid-template-columns:repeat(2,1fr)}} main{{padding:28px 14px}}}}
</style></head><body><main>
<h1>나의 집중 일정</h1>
<div class="sub">{started_at:%Y년 %m월 %d일}<br>기록 구간 {started_at:%H:%M:%S} — {observed_end:%H:%M:%S}</div>
<section class="metrics">{summary_cards}</section>
<section class="panel"><div class="headline"><div><h2>시간 흐름</h2><span class="sub">상태가 바뀐 구간을 한눈에 확인하세요.</span></div><div class="ratio">집중 {focus_ratio:.1f}%</div></div>
<div class="timeline">{timeline_segments}</div><div class="axis"><span>{started_at:%H:%M:%S}</span><span>{observed_end:%H:%M:%S}</span></div></section>
<section class="panel"><h2>구간별 일정</h2><div class="table-wrap"><table>
<thead><tr><th>시작</th><th>종료</th><th>상태</th><th>지속 시간</th></tr></thead><tbody>{schedule_rows}</tbody>
</table></div></section>
<div class="sub">리포트 생성: {generated_at:%Y-%m-%d %H:%M:%S}</div>
</main></body></html>"""


report_manager: ReportManager = ReportManager.get_instance()
