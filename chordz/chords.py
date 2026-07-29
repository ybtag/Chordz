"""Chord estimation (Stage 1): template matching on beat-synced chroma.

This is the no-AI baseline. For each beat segment we average the chroma and
pick the major/minor triad template with the highest cosine similarity. A low
similarity is reported as "N" (no chord). Accuracy is modest on real mixes;
Stage 2 replaces this with an ML backend.
"""
from __future__ import annotations

import numpy as np

# Pitch classes in order, using sharps (matching librosa's chroma ordering).
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Intervals (semitones from root) for the supported triad qualities.
_MAJOR = (0, 4, 7)   # root, major third, perfect fifth
_MINOR = (0, 3, 7)   # root, minor third, perfect fifth


def _triad_template(root: int, intervals: tuple[int, ...]) -> np.ndarray:
    """Build a unit-norm 12-dim binary pitch-class template for a chord."""
    tmpl = np.zeros(12, dtype=np.float32)
    for i in intervals:
        tmpl[(root + i) % 12] = 1.0
    n = float(np.linalg.norm(tmpl))
    if n > 0:
        tmpl = tmpl / n
    return tmpl


def build_templates() -> dict[str, np.ndarray]:
    """Build major and minor triad templates keyed by ``"ROOT:quality"``.

    Returns 24 entries (12 majors + 12 minors), each a unit-norm 12-vector.
    """
    templates: dict[str, np.ndarray] = {}
    for r in range(12):
        name = PITCH_CLASSES[r]
        templates[f"{name}:maj"] = _triad_template(r, _MAJOR)
        templates[f"{name}:min"] = _triad_template(r, _MINOR)
    return templates


def _frame_to_time(frame: int, sr: int, hop_length: int) -> float:
    return frame * hop_length / sr


def _symbol(root: str | None, quality: str) -> str:
    """Compact chord symbol, e.g. C:maj -> 'C', A:min -> 'Am', C:7 -> 'C7'."""
    if root is None or quality == "no-chord":
        return "N"
    suffix = {
        "maj": "", "min": "m", "7": "7",
        "maj7": "maj7", "min7": "m7", "dim": "dim",
    }.get(quality, "")
    return root + suffix


def compute_segments(
    chroma: np.ndarray,
    beat_frames: np.ndarray,
    sr: int,
    hop_length: int = 512,
    fallback_segment_seconds: float = 0.5,
) -> list[dict]:
    """Split the chroma into segments and return per-segment info.

    Boundaries come from ``beat_frames`` when available; otherwise the signal
    is sliced into fixed ``fallback_segment_seconds`` windows (e.g. a sustained
    intro with no detectable beats). Each returned dict carries the segment's
    start/end times (s), start/end frames, and the unit-norm average chroma
    vector -- shared by both template matching (Stage 1) and the HMM (Stage 2).
    """
    n_frames = chroma.shape[1] if chroma.ndim == 2 else 0
    if n_frames == 0:
        return []

    if beat_frames is None or len(beat_frames) == 0:
        frames_per_seg = max(1, int(round(fallback_segment_seconds * sr / hop_length)))
        bounds = list(range(0, n_frames, frames_per_seg))
        if not bounds:
            bounds = [0]
        if bounds[-1] != n_frames - 1:
            bounds.append(n_frames - 1)
        bounds = np.asarray(bounds, dtype=np.int64)
    else:
        bf = np.clip(np.asarray(beat_frames, dtype=np.int64), 0, n_frames - 1)
        bounds = np.unique(np.concatenate([[0], bf, [n_frames - 1]]))

    segments: list[dict] = []
    for i in range(len(bounds) - 1):
        a, b = int(bounds[i]), int(bounds[i + 1])
        if b < a:
            b = a
        seg = chroma[:, a:b + 1]
        if seg.shape[1] == 0:
            continue
        avg = seg.mean(axis=1)
        nrm = float(np.linalg.norm(avg))
        vec = avg / nrm if nrm > 1e-6 else avg  # both unit/zero -> cosine works
        segments.append({
            "start": round(_frame_to_time(a, sr, hop_length), 3),
            "end": round(_frame_to_time(b + 1, sr, hop_length), 3),
            "start_frame": a,
            "end_frame": b,
            "chroma": vec,
        })
    return segments


def estimate_chords(
    chroma: np.ndarray,
    beat_frames: np.ndarray,
    sr: int,
    hop_length: int = 512,
    no_chord_threshold: float = 0.2,
    fallback_segment_seconds: float = 0.5,
) -> list[dict]:
    """Estimate a chord for each segment via template matching (Stage 1).

    Segments are shared with ``compute_segments``; for each, the averaged
    chroma is matched to major/minor triad templates by cosine similarity, and
    a low best similarity is reported as "N" (no chord). For the ML path see
    ``ml_backend`` (Stage 2).
    """
    templates = build_templates()
    labels = list(templates.keys())
    T = np.stack([templates[lbl] for lbl in labels])  # (24, 12), unit-norm rows

    out: list[dict] = []
    for seg in compute_segments(chroma, beat_frames, sr, hop_length, fallback_segment_seconds):
        vec = seg["chroma"]
        scores = T @ vec  # cosine similarity (both sides unit-norm)
        best = int(np.argmax(scores))
        best_score = float(scores[best])
        if best_score < no_chord_threshold:
            root, quality = None, "no-chord"
        else:
            root, quality = labels[best].split(":")
        out.append({
            "start": seg["start"],
            "end": seg["end"],
            "symbol": _symbol(root, quality),
            "root": root,
            "quality": quality,
            "bass": root,
            "score": round(best_score, 4),
        })
    return out
