"""Generate a synthetic chord-progression test tone (pure stdlib, no deps).

Creates a WAV with a clean progression, each chord sustained ~1.5s with a short
silent gap, so chord changes are unambiguous. Used to validate multi-chord
detection, 7th-chord symbols, and voice-leading end-to-end.

Run:
  python examples/make_progression_test.py           # pop: C - G - Am - F
  python examples/make_progression_test.py jazz      # jazz: Cmaj7 - Am7 - Dm7 - G7 - Cmaj7
Output: examples/progression_test.wav  (or examples/jazz_progression_test.wav)
"""
import math
import os
import struct
import sys
import wave

SR = 22050
CHORD_DUR = 1.5
GAP = 0.06
AMP = 0.4

# (name, [frequencies Hz]) -- chroma is octave-invariant, so octave is free.
PROGRESSIONS = {
    "pop": [
        ("C",  [261.63, 329.63, 392.00]),
        ("G",  [196.00, 246.94, 293.66]),
        ("Am", [220.00, 261.63, 329.63]),
        ("F",  [174.61, 220.00, 261.63]),
    ],
    "jazz": [
        ("Cmaj7", [261.63, 329.63, 392.00, 493.88]),
        ("Am7",   [220.00, 261.63, 329.63, 392.00]),
        ("Dm7",   [146.83, 174.61, 220.00, 261.63]),
        ("G7",    [196.00, 246.94, 293.66, 349.23]),
        ("Cmaj7", [261.63, 329.63, 392.00, 493.88]),
    ],
}


def _chord_samples(freqs, n_samples):
    frames = bytearray()
    for i in range(n_samples):
        t = i / SR
        s = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
        fin = min(1.0, i / (SR * 0.02))
        fout = min(1.0, (n_samples - i) / (SR * 0.02))
        fade = min(fin, fout)
        val = max(-1.0, min(1.0, s * AMP * fade))
        frames += struct.pack("<h", int(val * 32767))
    return frames


def main() -> None:
    preset = sys.argv[1] if len(sys.argv) > 1 else "pop"
    progression = PROGRESSIONS.get(preset, PROGRESSIONS["pop"])
    fname = "progression_test.wav" if preset == "pop" else f"{preset}_progression_test.wav"
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)

    n_chord = int(SR * CHORD_DUR)
    n_gap = int(SR * GAP)
    silence = b"\x00\x00" * n_gap
    frames = bytearray()
    for _name, freqs in progression:
        frames += _chord_samples(freqs, n_chord)
        frames += silence

    with wave.open(out, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))

    names = " - ".join(n for n, _ in progression)
    print(f"wrote {out} ({len(progression)} chords: {names})")


if __name__ == "__main__":
    main()

