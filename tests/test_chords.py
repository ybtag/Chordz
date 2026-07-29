"""Unit tests for chord template matching (pure numpy; no librosa needed)."""
import numpy as np

from chordz.chords import build_templates, estimate_chords


def _chroma_from_pitches(pitches, n_frames=10):
    """Build a unit-norm-per-frame chroma with energy on the given pitch classes."""
    chroma = np.zeros((12, n_frames), dtype=np.float32)
    for pc in pitches:
        chroma[pc, :] = 1.0
    norms = np.linalg.norm(chroma, axis=0, keepdims=True)
    norms[norms == 0] = 1.0
    return (chroma / norms).astype(np.float32)


def test_build_templates_count():
    t = build_templates()
    assert len(t) == 24  # 12 majors + 12 minors


def test_templates_unit_norm():
    for v in build_templates().values():
        assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-5


def test_estimate_c_major():
    chroma = _chroma_from_pitches((0, 4, 7))  # C, E, G
    segs = estimate_chords(chroma, np.array([], dtype=np.int64), sr=22050)
    assert len(segs) == 1
    assert segs[0]["root"] == "C"
    assert segs[0]["quality"] == "maj"
    assert segs[0]["symbol"] == "C"


def test_estimate_a_minor():
    chroma = _chroma_from_pitches((9, 0, 4))  # A, C, E
    segs = estimate_chords(chroma, np.array([], dtype=np.int64), sr=22050)
    assert len(segs) == 1
    assert segs[0]["root"] == "A"
    assert segs[0]["quality"] == "min"
    assert segs[0]["symbol"] == "Am"


def test_estimate_silence_is_no_chord():
    chroma = np.zeros((12, 8), dtype=np.float32)
    segs = estimate_chords(chroma, np.array([], dtype=np.int64), sr=22050)
    assert len(segs) == 1
    assert segs[0]["symbol"] == "N"


def test_estimate_fallback_segments_when_no_beats():
    # A long C-major chroma with NO beats must be segmented by the fixed-length
    # fallback (not collapsed into one segment).
    chroma = _chroma_from_pitches((0, 4, 7), n_frames=200)  # ~4.6s at 22050/512
    segs = estimate_chords(chroma, np.array([], dtype=np.int64), sr=22050)
    assert len(segs) > 1
    assert all(s["symbol"] == "C" for s in segs)
