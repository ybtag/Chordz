"""JSON renderer: write the canonical ChordTimeline to disk."""
from __future__ import annotations

from pathlib import Path

from ..timeline import ChordTimeline


def render_json_file(timeline: ChordTimeline, out_path: str | Path) -> str:
    """Write the timeline as JSON. Returns the path written."""
    p = Path(out_path)
    p.write_text(timeline.to_json(), encoding="utf-8")
    return str(p)
