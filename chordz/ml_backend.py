"""Stage 2 ML backend: an HMM-based chord recognizer (numpy-only).

This is the classic, pre-deep-learning approach to automatic chord recognition
(see CREDITS.md): per-segment chroma emissions over an expanded chord
vocabulary, Krumhansl-Schmuckler key estimation to bias diatonic chords, and
Viterbi decoding to enforce temporal smoothness.

It runs on the same librosa/numpy stack as Stage 1 (no extra dependencies),
is fully local, and is MIT-clean (see NOTICE.md). It uses a pure-numpy HMM
plus optional Demucs separation (Stage 2b, planned).
"""
from __future__ import annotations

import numpy as np

from .chords import PITCH_CLASSES, _symbol, compute_segments

# Expanded chord vocabulary: (quality -> semitone intervals from the root).
_CHORD_INTERVALS: dict[str, tuple[int, ...]] = {
    "maj":  (0, 4, 7),
    "min":  (0, 3, 7),
    "7":    (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "dim":  (0, 3, 6),
}

# Krumhansl-Schmuckler key profiles (pitch-class salience, C-indexed).
_KS_MAJOR = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.70, 2.80, 3.52, 5.38, 2.60, 3.53, 2.54, 4.00],
    dtype=np.float64,
)
_KS_MINOR = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=np.float64,
)


def _build_expanded_templates() -> tuple[list[str], np.ndarray]:
    """Return (labels, templates) for the 72-chord vocabulary, unit-norm rows."""
    labels: list[str] = []
    tmpls: list[np.ndarray] = []
    for r in range(12):
        name = PITCH_CLASSES[r]
        for q, ints in _CHORD_INTERVALS.items():
            t = np.zeros(12, dtype=np.float32)
            for i in ints:
                t[(r + i) % 12] = 1.0
            n = float(np.linalg.norm(t))
            if n:
                t = t / n
            labels.append(f"{name}:{q}")
            tmpls.append(t)
    return labels, np.stack(tmpls)  # (72, 12), unit-norm rows


def _major_scale(root: int) -> set[int]:
    return {(root + s) % 12 for s in (0, 2, 4, 5, 7, 9, 11)}


def _minor_scale(root: int) -> set[int]:
    return {(root + s) % 12 for s in (0, 2, 3, 5, 7, 8, 10)}


def estimate_key(chroma: np.ndarray) -> tuple[int, str]:
    """Estimate the musical key as (root pitch-class index, mode) using
    Krumhansl-Schmuckler correlation of the global chroma with rotated
    major/minor profiles."""
    profile = chroma.mean(axis=1) if chroma.ndim == 2 else np.asarray(chroma)
    profile = np.asarray(profile, dtype=np.float64)
    n = float(np.linalg.norm(profile))
    if n > 0:
        profile = profile / n

    best = (-1, "maj")
    best_score = -np.inf
    for r in range(12):
        for mode, prof in (("maj", _KS_MAJOR), ("min", _KS_MINOR)):
            rotated = np.roll(prof, r)
            pn = float(np.linalg.norm(rotated))
            score = float(np.dot(rotated / pn, profile)) if pn > 0 else 0.0
            if score > best_score:
                best_score = score
                best = (r, mode)
    return best


class MLBackend:
    """Abstract ML backend interface (Stage 2)."""

    name = "abstract"

    def estimate(
        self,
        chroma: np.ndarray,
        beat_frames: np.ndarray,
        sr: int,
        hop_length: int = 512,
        no_chord_threshold: float = 0.2,
        fallback_segment_seconds: float = 0.5,
    ) -> list[dict]:
        raise NotImplementedError


class HMMBackend(MLBackend):
    """HMM chord recognizer: expanded vocabulary + key prior + Viterbi.

    Emission (log) per segment/state = beta * cos(chroma, template) plus a key
    prior that boosts chords whose root lies in the estimated key's scale. The
    transition model uses a flat change penalty: staying costs 0, switching to
    any other chord costs -change_penalty. This is the standard, well-behaved
    chord-HMM transition -- a probabilistic stay/move split would over-penalise
    switching across a large state space and "stick" to a wrong bridge chord. A
    segment whose best raw cosine is below no_chord_threshold is reported as
    "N" (no chord).
    """

    name = "hmm"

    def __init__(
        self, beta: float = 8.0, change_penalty: float = 2.0, key_bonus: float = 1.0
    ) -> None:
        self.beta = beta
        self.change_penalty = change_penalty
        self.key_bonus = key_bonus
        self.labels, self.T = _build_expanded_templates()

    def estimate(
        self,
        chroma: np.ndarray,
        beat_frames: np.ndarray,
        sr: int,
        hop_length: int = 512,
        no_chord_threshold: float = 0.2,
        fallback_segment_seconds: float = 0.5,
    ) -> list[dict]:
        segments = compute_segments(
            chroma, beat_frames, sr, hop_length, fallback_segment_seconds
        )
        if not segments:
            return []

        key_root, key_mode = estimate_key(chroma)
        scale = _major_scale(key_root) if key_mode == "maj" else _minor_scale(key_root)
        key_label = PITCH_CLASSES[key_root] + ("m" if key_mode == "min" else "")

        roots = np.array(
            [PITCH_CLASSES.index(lbl.split(":")[0]) for lbl in self.labels], dtype=np.int64
        )
        in_scale = np.array([(int(r) in scale) for r in roots], dtype=np.float64)
        log_prior = self.key_bonus * in_scale  # additive in log space

        emits: list[np.ndarray] = []
        raw_cos: list[float] = []
        for seg in segments:
            vec = seg["chroma"]
            cos = self.T @ vec  # (n,) cosine (both unit-norm)
            emits.append(self.beta * cos + log_prior)
            raw_cos.append(float(cos.max()))
        emits_arr = np.stack(emits)

        path = self._viterbi(emits_arr)

        out: list[dict] = []
        for seg, state_idx, rc in zip(segments, path, raw_cos):
            if rc < no_chord_threshold:
                root, quality = None, "no-chord"
            else:
                root, quality = self.labels[int(state_idx)].split(":")
            out.append({
                "start": seg["start"],
                "end": seg["end"],
                "symbol": _symbol(root, quality),
                "root": root,
                "quality": quality,
                "bass": root,
                "score": round(rc, 4),
                "key": key_label,
            })
        return out

    def _viterbi(self, emits: np.ndarray) -> np.ndarray:
        """Viterbi decode with a flat change penalty. Staying costs 0; moving
        to a different state costs -change_penalty. Returns the best state
        index per timestep."""
        T_len, n = emits.shape
        if T_len == 0:
            return np.array([], dtype=np.int64)
        if T_len == 1:
            return np.array([int(np.argmax(emits[0]))], dtype=np.int64)

        penalty = self.change_penalty
        states = np.arange(n)
        delta = emits[0].astype(np.float64).copy()
        back = np.zeros((T_len, n), dtype=np.int64)
        for t in range(1, T_len):
            order = np.argsort(delta)[::-1]
            top1, top2 = int(order[0]), int(order[1]) if n > 1 else int(order[0])
            top1v = float(delta[top1])
            top2v = float(delta[top2]) if n > 1 else -np.inf
            best_other = np.where(states == top1, top2v, top1v)  # max_{i!=j} delta[i]
            stay = delta                    # transition cost 0 to stay
            change = best_other - penalty   # transition cost -penalty to change
            delta = emits[t] + np.maximum(stay, change)
            back_prev = np.where(states == top1, top2, top1)  # source achieving best_other
            back[t] = np.where(stay >= change, states, back_prev)

        path = np.zeros(T_len, dtype=np.int64)
        path[-1] = int(np.argmax(delta))
        for t in range(T_len - 2, -1, -1):
            path[t] = back[t + 1, path[t + 1]]
        return path


def get_ml_backend() -> MLBackend | None:
    """Return the best available ML backend.

    Currently always returns the numpy-only HMMBackend (no optional
    dependencies). This is the default ML path used by --ml.
    """
    return HMMBackend()
