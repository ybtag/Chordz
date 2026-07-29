"""Chordz command-line interface.

Examples
--------
    chordz song.mp3
    chordz song.mp3 --text song.chords.txt
    chordz song.mp3 --sr 44100 --hop 512
    chordz song.mp3 --ml                       # Stage 2 HMM backend
    chordz song.mp3 --separate --ml            # Demucs stems, then HMM
    chordz song.mp3 --separate --ml --device xpu   # force Intel GPU
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

from . import __version__
from .audio_io import load_audio
from .chords import estimate_chords
from .features import compute_beats, compute_chroma
from .ml_backend import get_ml_backend
from .renderers.json_out import render_json_file
from .renderers.text import render_text
from .timeline import build_timeline
from .voicings import attach_voicings


def analyze(
    path: str,
    sr: int = 22050,
    hop: int = 512,
    use_ml: bool = False,
    separate: bool = False,
    device: str = "auto",
):
    """Run the analysis pipeline and return a ChordTimeline.

    With ``use_ml=True`` the Stage 2 HMM backend is used (numpy-only);
    otherwise Stage 1 template matching is used. With ``separate=True`` the
    song is first split with Demucs and analysis runs on the harmonic
    accompaniment ('other' + 'bass'), ignoring vocals/drums. ``device`` selects
    the Demucs device: 'auto' (cuda -> xpu -> cpu) or a specific backend.
    """
    import librosa  # local import keeps module import side-effects minimal

    if separate:
        from .separation import is_available, separate_accompaniment
        if is_available():
            y, sr = separate_accompaniment(path, target_sr=sr, device=device)
        else:
            warnings.warn(
                "Demucs/torch not installed; --separate disabled, using full mix.",
                stacklevel=2,
            )
            y, sr = load_audio(path, sr=sr)
    else:
        y, sr = load_audio(path, sr=sr)

    chroma = compute_chroma(y, sr, hop_length=hop)
    beat_times, beat_frames = compute_beats(y, sr, hop_length=hop)

    if use_ml:
        backend = get_ml_backend()
        if backend is None:
            warnings.warn(
                "No ML backend available; falling back to template matching.",
                stacklevel=2,
            )
            segments = estimate_chords(chroma, beat_frames, sr, hop_length=hop)
        else:
            segments = backend.estimate(chroma, beat_frames, sr, hop_length=hop)
    else:
        segments = estimate_chords(chroma, beat_frames, sr, hop_length=hop)

    segments = attach_voicings(segments)

    duration = float(librosa.get_duration(y=y, sr=sr))
    key = None
    if segments and segments[0].get("key"):
        key = segments[0]["key"]
    audio_meta = {
        "file": Path(path).name,
        "sample_rate": sr,
        "duration": duration,
        "key": key,
        "separated": separate,
    }
    return build_timeline(audio_meta, beat_times.tolist(), segments)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chordz",
        description="Analyze an audio file and output time-aligned guitar chords.",
    )
    p.add_argument("audio", help="Path to audio file (mp3, wav, flac, m4a, ...)")
    p.add_argument(
        "--out", default=None, help="Output JSON path (default: <audio>.chordz.json)"
    )
    p.add_argument(
        "--text", default=None, help="Output text chord-sheet path"
    )
    p.add_argument("--sr", type=int, default=22050, help="Sample rate in Hz")
    p.add_argument("--hop", type=int, default=512, help="Hop length (frames)")
    p.add_argument(
        "--separate",
        action="store_true",
        help="Pre-separate with Demucs (Stage 2b); needs torch+demucs installed",
    )
    p.add_argument(
        "--device",
        choices=("auto", "cuda", "xpu", "cpu"),
        default="auto",
        help="Demucs device: auto (cuda->xpu->cpu) or a specific backend (Intel=xpu)",
    )
    p.add_argument(
        "--ml",
        action="store_true",
        help="Use the Stage 2 HMM ML backend (else Stage 1 template matching)",
    )
    p.add_argument("--version", action="version", version=f"chordz {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"error: audio file not found: {audio_path}", file=sys.stderr)
        return 2

    timeline = analyze(
        str(audio_path),
        sr=args.sr,
        hop=args.hop,
        use_ml=args.ml,
        separate=args.separate,
        device=args.device,
    )

    out_json = args.out or str(audio_path.with_suffix(".chordz.json"))
    render_json_file(timeline, out_json)

    text = render_text(timeline)
    if args.text:
        Path(args.text).write_text(text, encoding="utf-8")
    print(text)
    print(f"\nJSON written to: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
