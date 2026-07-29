"""Tests for Stage 4 player logic (pure; no tkinter/audio needed)."""
from chordz.player import find_segment, map_to_original_time


def test_find_segment_returns_active():
    tl = {"segments": [
        {"start": 0.0, "end": 1.0, "symbol": "C"},
        {"start": 1.0, "end": 2.0, "symbol": "G"},
        {"start": 2.0, "end": 3.0, "symbol": "Am"},
    ]}
    assert find_segment(tl, 0.0)["symbol"] == "C"
    assert find_segment(tl, 0.5)["symbol"] == "C"
    assert find_segment(tl, 1.5)["symbol"] == "G"
    assert find_segment(tl, 2.9)["symbol"] == "Am"


def test_find_segment_beyond_or_before_returns_edge():
    tl = {"segments": [{"start": 1.0, "end": 2.0, "symbol": "G"}]}
    assert find_segment(tl, 5.0)["symbol"] == "G"  # beyond end -> last
    assert find_segment(tl, 0.5)["symbol"] == "G"  # before first -> first


def test_find_segment_empty():
    assert find_segment({}, 0.0) is None
    assert find_segment({"segments": []}, 0.0) is None


def test_map_to_original_time():
    # half speed: a position 4.0s into the slowed file is 2.0s of original song
    assert map_to_original_time(4.0, 0.5) == 2.0
    # full speed: identity
    assert map_to_original_time(3.0, 1.0) == 3.0
    # 0.75x: 3.0s slowed -> 2.25s original
    assert abs(map_to_original_time(3.0, 0.75) - 2.25) < 1e-9

