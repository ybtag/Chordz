"""Feature extraction: chroma (CQT) and beat tracking.

The chroma (pitch-class profile) collapses the spectrum into the 12 pitch
classes (C, C#, ..., B), which maps directly to chord roots. Beat tracking
gives the boundaries on which chords change.
"""
from __future__ import annotations

import librosa
import numpy as np


def compute_chroma(y: np.ndarray, sr: int, hop_length: int = 512) -> np.ndarray:
    """Compute a constant-Q chromagram (12 pitch classes) for the signal.

    Returns a (12, n_frames) float32 array with each column (frame) normalized
    to unit L2 norm so that cosine similarity to chord templates is meaningful.
    """
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length, n_chroma=12)
    # Guard against librosa returning a non-contiguous array.
    chroma = np.asarray(chroma, dtype=np.float32)
    if chroma.ndim == 1:
        chroma = chroma.reshape(12, -1)
    norms = np.linalg.norm(chroma, axis=0, keepdims=True)
    norms[norms == 0] = 1.0
    return (chroma / norms).astype(np.float32)


def compute_beats(
    y: np.ndarray, sr: int, hop_length: int = 512
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate beat times (seconds) and beat frame indices.

    Returns
    -------
    beat_times : np.ndarray[float]
        Beat locations in seconds.
    beat_frames : np.ndarray[int]
        Corresponding frame indices (in hop-length units).

    If beat tracking fails (e.g. near-silent audio), empty arrays are returned
    so the caller can fall back to one segment spanning the whole song.
    """
    try:
        _tempo, beat_frames = librosa.beat.beat_track(
            y=y, sr=sr, hop_length=hop_length
        )
    except Exception:
        return np.array([], dtype=np.float64), np.array([], dtype=np.int64)

    beat_frames = np.asarray(beat_frames, dtype=np.int64)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)
    return np.asarray(beat_times, dtype=np.float64), beat_frames
