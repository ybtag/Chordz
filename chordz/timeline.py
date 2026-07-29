"""ChordTimeline data model and JSON serialization.

The timeline is the canonical output of the analyzer and the input to all
renderers (text now, graphical player in a later stage). Keeping it structured
and time-aligned means a future player can render chords synced to playback.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Voicing:
    """A single guitar fingering for a chord.

    Attributes
    ----------
    frets : list[int]
        Per-string fret numbers, low-E -> high-E. -1 = muted, 0 = open.
    fingers : list[int]
        Per-string finger assignment (0 = open/none, 1-4 = fingers).
    base_fret : int
        The fret position the diagram is drawn from (1 = nut).
    name : str
        Human-readable label (e.g. "C open").
    """

    frets: list[int]
    fingers: list[int]
    base_fret: int = 1
    name: str = ""


@dataclass
class ChordSegment:
    start: float
    end: float
    root: str | None
    quality: str
    bass: str | None
    symbol: str
    score: float = 0.0
    voicings: list[Voicing] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "root": self.root,
            "quality": self.quality,
            "bass": self.bass,
            "symbol": self.symbol,
            "score": self.score,
            "voicings": [
                {
                    "frets": v.frets,
                    "fingers": v.fingers,
                    "base_fret": v.base_fret,
                    "name": v.name,
                }
                for v in self.voicings
            ],
        }


@dataclass
class ChordTimeline:
    """A complete, time-aligned chord analysis of one audio file."""

    audio: dict[str, Any]
    beats: list[float]
    segments: list[ChordSegment]

    def to_dict(self) -> dict:
        return {
            "audio": self.audio,
            "beats": list(self.beats),
            "segments": [s.to_dict() for s in self.segments],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def build_timeline(
    audio_meta: dict[str, Any], beats: list[float], segments: list[dict]
) -> ChordTimeline:
    """Build a ChordTimeline from raw segment dicts (as produced by the
    analyzer after voicings are attached)."""
    built: list[ChordSegment] = []
    for s in segments:
        voicings = [
            Voicing(
                frets=list(v["frets"]),
                fingers=list(v["fingers"]),
                base_fret=int(v.get("base_fret", 1)),
                name=str(v.get("name", "")),
            )
            for v in s.get("voicings", [])
        ]
        built.append(
            ChordSegment(
                start=float(s["start"]),
                end=float(s["end"]),
                root=s.get("root"),
                quality=str(s.get("quality", "")),
                bass=s.get("bass", s.get("root")),
                symbol=str(s.get("symbol", "N")),
                score=float(s.get("score", 0.0)),
                voicings=voicings,
            )
        )
    return ChordTimeline(
        audio=dict(audio_meta), beats=list(beats), segments=built
    )
