"""Unit tests for the ChordTimeline data model (no librosa needed)."""
import json

from chordz.timeline import Voicing, build_timeline


def _sample_segments():
    return [
        {
            "start": 0.0,
            "end": 1.0,
            "symbol": "C",
            "root": "C",
            "quality": "maj",
            "bass": "C",
            "score": 0.9,
            "voicings": [
                {"frets": [-1, 3, 2, 0, 1, 0], "fingers": [0, 3, 2, 0, 1, 0],
                 "base_fret": 1, "name": "C open"}
            ],
        }
    ]


def test_timeline_serializes_to_dict():
    tl = build_timeline(
        {"file": "x.mp3", "sample_rate": 22050, "duration": 2.0, "key": None},
        [0.0, 1.0],
        _sample_segments(),
    )
    d = tl.to_dict()
    assert d["audio"]["duration"] == 2.0
    assert d["segments"][0]["symbol"] == "C"
    assert d["segments"][0]["voicings"][0]["frets"] == [-1, 3, 2, 0, 1, 0]


def test_timeline_json_roundtrip():
    tl = build_timeline(
        {"file": "x.mp3", "sample_rate": 22050, "duration": 2.0, "key": None},
        [0.0, 1.0],
        _sample_segments(),
    )
    j = json.loads(tl.to_json())
    assert j["segments"][0]["voicings"][0]["name"] == "C open"
    assert j["beats"] == [0.0, 1.0]


def test_voicing_dataclass_to_dict():
    v = Voicing(frets=[0, 0, 0, 0, 0, 0], fingers=[0, 0, 0, 0, 0, 0],
                base_fret=1, name="test")
    assert v.frets == [0, 0, 0, 0, 0, 0]
