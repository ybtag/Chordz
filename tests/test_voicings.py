"""Unit tests for guitar voicing generation + voice-leading (no librosa)."""
from chordz.voicings import _generate_movable, _parse, attach_voicings


def test_parse_major():
    assert _parse("C") == ("C", "maj")


def test_parse_minor():
    assert _parse("Cm") == ("C", "min")
    assert _parse("F#m") == ("F#", "min")


def test_parse_seventh():
    assert _parse("C7") == ("C", "7")
    assert _parse("Cmaj7") == ("C", "maj7")
    assert _parse("Cm7") == ("C", "min7")


def test_generate_movable_for_uncommon_root():
    v = _generate_movable("C#")
    assert len(v) >= 1
    assert "frets" in v[0]
    assert len(v[0]["frets"]) == 6


def test_generate_movable_for_seventh():
    v = _generate_movable("F#7")
    assert len(v) >= 1
    assert len(v[0]["frets"]) == 6


def test_attach_uses_known_open_shape_for_C():
    segs = [{"start": 0.0, "end": 1.0, "symbol": "C", "root": "C", "quality": "maj"}]
    out = attach_voicings(segs)
    assert len(out[0]["voicings"]) >= 1
    assert out[0]["voicings"][0]["frets"][0] == -1  # C open mutes low E


def test_attach_generates_barre_for_F_sharp_minor():
    segs = [{"start": 0.0, "end": 1.0, "symbol": "F#m", "root": "F#", "quality": "min"}]
    out = attach_voicings(segs)
    assert len(out[0]["voicings"]) >= 1


def test_attach_no_chord_empty():
    segs = [{"start": 0.0, "end": 1.0, "symbol": "N", "root": None, "quality": "no-chord"}]
    out = attach_voicings(segs)
    assert out[0]["voicings"] == []


def test_voice_leading_prefers_nearby_voicing():
    # C (open, low) then F: F's candidates include a low E-shape barre (~fret 1)
    # and a high A-shape barre (~fret 8). After C open, voice-leading should
    # pick the low F barre, not the high one.
    segs = [
        {"symbol": "C", "root": "C", "quality": "maj"},
        {"symbol": "F", "root": "F", "quality": "maj"},
    ]
    out = attach_voicings(segs)
    f_chosen = out[1]["voicings"][0]  # chosen voicing is first in the list
    assert f_chosen["frets"][0] == 1  # low E-shape F barre (fret 1), not the high one

