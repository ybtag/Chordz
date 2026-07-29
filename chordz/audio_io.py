"""Audio input: load an MP3 (or any librosa-supported file) as mono PCM."""
from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np


def load_audio(path: str | Path, sr: int = 22050, mono: bool = True) -> tuple[np.ndarray, int]:
    """Load an audio file as a mono waveform at a target sample rate.

    Parameters
    ----------
    path : str | Path
        Path to the audio file (mp3, wav, flac, m4a, ...).
    sr : int
        Target sample rate in Hz. 22050 is a good default for chroma analysis.
    mono : bool
        Downmix multi-channel audio to mono.

    Returns
    -------
    (y, sr) : (np.ndarray[float32], int)
        Waveform samples (mono, 1-D) and the sample rate actually used.

    Notes
    -----
    MP3 decoding requires ``soundfile >= 0.11`` (via libsndfile); otherwise
    librosa falls back to the ``audioread`` backend.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    y, sr_out = librosa.load(str(path), sr=sr, mono=mono)
    # librosa returns float32 in [-1, 1]; force 1-D mono just in case.
    if y.ndim > 1:
        y = np.mean(y, axis=0)
    return y.astype(np.float32), int(sr_out)
