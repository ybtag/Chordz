"""Stage 2b: optional Demucs source separation (preprocessing).

When enabled (--separate), the input song is split into stems with Demucs
(htdemucs) and chord analysis runs on the harmonic accompaniment (the 'other'
+ 'bass' stems), excluding vocals (non-chordal) and drums (broadband noise).
This yields far cleaner chroma on real mixes.

MIT-licensed (Demucs + PyTorch), opt-in, NOT in the default build. The heavy
dependencies (torch, demucs) are imported lazily and only when --separate is
used; if they are not installed, the flag falls back to the full mix.
"""
from __future__ import annotations

import numpy as np


def is_available() -> bool:
    """True if demucs + torch are importable."""
    try:
        import demucs  # noqa: F401
        import torch  # noqa: F401
    except Exception:
        return False
    return True


def pick_device() -> str:
    """Pick the best available torch device: NVIDIA cuda -> Intel xpu -> cpu.

    Safe on CPU-only torch builds (where ``torch.xpu`` may not exist).
    """
    import torch
    if torch.cuda.is_available():
        return "cuda"
    xpu = getattr(torch, "xpu", None)
    if xpu is not None and xpu.is_available():
        return "xpu"
    return "cpu"


def separate_accompaniment(
    path: str,
    target_sr: int = 22050,
    model_name: str = "htdemucs",
    device: str = "auto",
) -> tuple[np.ndarray, int]:
    """Separate an audio file with Demucs and return the harmonic
    accompaniment ('other' + 'bass' stems) as a mono float32 waveform at
    ``target_sr``.

    ``device='auto'`` picks cuda -> xpu (Intel) -> cpu, and falls back to CPU
    if the chosen device fails (e.g. a half-installed GPU stack). Both NVIDIA
    and Intel GPUs are supported this way; only the runtime/drivers differ.

    Raises ImportError if demucs/torch are not installed.
    """
    import librosa
    import torch
    from demucs.api import Separator

    if device == "auto":
        device = pick_device()
    devices_to_try = [device] if device == "cpu" else [device, "cpu"]

    stems = None
    model_sr = None
    for dev in devices_to_try:
        try:
            sep = Separator(model=model_name, device=dev, progress=False)
            _origin, stems = sep.separate_audio_file(str(path))
            model_sr = int(sep.samplerate)
            break
        except Exception:
            if dev == "cpu":
                raise  # even CPU failed -- let the caller see the error

    # Harmonic accompaniment = 'other' (keys/guitar) + 'bass' (root). This
    # excludes 'vocals' (non-chordal) and 'drums' (broadband). Fall back to the
    # first available stem if the model uses non-standard source names.
    acc = None
    for name in ("other", "bass"):
        t = stems.get(name)
        if t is not None:
            t = t.to(torch.float32)
            acc = t if acc is None else acc + t
    if acc is None and stems:
        acc = next(iter(stems.values())).to(torch.float32)
    if acc is None:
        raise RuntimeError("Demucs returned no stems")

    # (channels, samples) -> mono (samples,)
    if acc.dim() > 1:
        acc = acc.mean(dim=0)
    wav = acc.detach().cpu().numpy().astype(np.float32)

    if model_sr != target_sr:
        wav = librosa.resample(wav, orig_sr=model_sr, target_sr=target_sr)
    return wav, target_sr
