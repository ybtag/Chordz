"""Tests for the Stage 2 HMM ML backend (pure numpy; no librosa needed)."""
import numpy as np

from chordz.ml_backend import HMMBackend, estimate_key, get_ml_backend


def _chroma_from_pitches(pitches, n_frames=10):
    chroma = np.zeros((12, n_frames), dtype=np.float32)
    for pc in pitches:
        chroma[pc, :] = 1.0
    norms = np.linalg.norm(chroma, axis=0, keepdims=True)
    norms[norms == 0] = 1.0
    return (chroma / norms).astype(np.float32)


def test_get_ml_backend_returns_hmm():
    b = get_ml_backend()
    assert isinstance(b, HMMBackend)


def test_estimate_key_c_major():
    chroma = _chroma_from_pitches((0, 4, 7), n_frames=40)  # C E G
    root, mode = estimate_key(chroma)
    assert root == 0 and mode == "maj"  # C major


def test_estimate_key_a_minor():
    chroma = _chroma_from_pitches((9, 0, 4), n_frames=40)  # A C E
    root, mode = estimate_key(chroma)
    assert root == 9 and mode == "min"  # A minor


def test_hmm_detects_c_major():
    chroma = _chroma_from_pitches((0, 4, 7), n_frames=10)
    segs = HMMBackend().estimate(chroma, np.array([], dtype=np.int64), sr=22050)
    assert len(segs) >= 1
    assert segs[0]["symbol"] == "C"
    assert segs[0]["quality"] == "maj"


def test_hmm_detects_a_minor():
    chroma = _chroma_from_pitches((9, 0, 4), n_frames=10)
    segs = HMMBackend().estimate(chroma, np.array([], dtype=np.int64), sr=22050)
    assert len(segs) >= 1
    assert segs[0]["symbol"] == "Am"
    assert segs[0]["quality"] == "min"


def test_hmm_fallback_segments_when_no_beats():
    chroma = _chroma_from_pitches((0, 4, 7), n_frames=200)  # ~4.6s
    segs = HMMBackend().estimate(chroma, np.array([], dtype=np.int64), sr=22050)
    assert len(segs) > 1
    assert all(s["symbol"] == "C" for s in segs)


def test_hmm_emits_key_label():
    chroma = _chroma_from_pitches((0, 4, 7), n_frames=10)
    segs = HMMBackend().estimate(chroma, np.array([], dtype=np.int64), sr=22050)
    assert segs[0].get("key") == "C"
