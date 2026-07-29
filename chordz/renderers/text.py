"""Text renderer: a human-readable chord sheet with timestamps."""
from __future__ import annotations

from ..timeline import ChordTimeline


def render_text(timeline: ChordTimeline) -> str:
    meta = timeline.audio
    lines: list[str] = []
    lines.append(f"# Chordz analysis: {meta.get('file', '?')}")
    duration = float(meta.get("duration", 0) or 0)
    lines.append(f"Duration: {duration:.1f}s   Key: {meta.get('key') or '?'}")
    lines.append("")

    for seg in timeline.segments:
        mm = int(seg.start // 60)
        ss = seg.start - mm * 60
        vlabel = ""
        if seg.voicings:
            v = seg.voicings[0]
            vlabel = f"   [{v.name}]"
        lines.append(
            f"[{mm:02d}:{ss:05.2f}] {seg.symbol:<6} (score {seg.score:.2f}){vlabel}"
        )
    return "\n".join(lines)
