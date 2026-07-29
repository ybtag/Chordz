"""Debug: inspect HMM per-segment emissions vs. the Viterbi path.

Run:  python examples/debug_hmm.py [audio]
"""
import os
import sys

import numpy as np
import librosa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chordz.features import compute_chroma
from chordz.chords import compute_segments, PITCH_CLASSES
from chordz.ml_backend import HMMBackend, estimate_key

audio = sys.argv[1] if len(sys.argv) > 1 else "examples/progression_test.wav"
y, sr = librosa.load(audio, sr=22050, mono=True)
chroma = compute_chroma(y, sr, hop_length=512)

b = HMMBackend()
segs = compute_segments(chroma, np.array([]), sr, 512, 0.5)
kr, km = estimate_key(chroma)
print("KEY:", PITCH_CLASSES[kr], km)

emits = []
for seg in segs:
    vec = seg["chroma"]
    cos = b.T @ vec
    emits.append(b.beta * cos + b.key_bonus * np.array(
        [(PITCH_CLASSES.index(lbl.split(":")[0]) in
          ({(kr+s)%12 for s in (0,2,4,5,7,9,11)} if km=="maj" else {(kr+s)%12 for s in (0,2,3,5,7,8,10)}))
         for lbl in b.labels], dtype=np.float64))
    top = np.argsort(cos)[::-1][:4]
    toppc = [PITCH_CLASSES[i] for i in np.argsort(seg["chroma"])[::-1][:4]]
    print(f"{seg['start']:6.2f}-{seg['end']:6.2f} topPC={toppc} "
          f"perSegBest={b.labels[int(np.argmax(cos))]}({cos.max():.2f}) "
          f"top4={[b.labels[i]+'('+f'{cos[i]:.2f}'+')' for i in top]}")

path = b._viterbi(np.stack(emits))
print("PATH:", [b.labels[i] for i in path])
