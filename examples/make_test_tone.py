"""Generate a synthetic C-major test tone (pure stdlib, no third-party deps).

Creates a WAV containing a sustained C major chord (C4, E4, G4) for a few
seconds, used to sanity-check the Stage 1 analyzer end-to-end.

Run:  python examples/make_test_tone.py
Output: examples/c_major_test.wav
"""
import math
import os
import struct
import wave

SR = 22050
DUR = 4.0
FREQS = [261.63, 329.63, 392.00]  # C4, E4, G4
AMP = 0.4
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "c_major_test.wav")


def main() -> None:
    n = int(SR * DUR)
    frames = bytearray()
    for i in range(n):
        t = i / SR
        s = sum(math.sin(2 * math.pi * f * t) for f in FREQS) / len(FREQS)
        # gentle fade in/out to avoid clicks
        fin = min(1.0, i / (SR * 0.05))
        fout = min(1.0, (n - i) / (SR * 0.05))
        fade = min(fin, fout)
        val = max(-1.0, min(1.0, s * AMP * fade))
        frames += struct.pack("<h", int(val * 32767))

    with wave.open(OUT, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))

    print(f"wrote {OUT} ({DUR:.1f}s, {SR} Hz, mono)")


if __name__ == "__main__":
    main()
