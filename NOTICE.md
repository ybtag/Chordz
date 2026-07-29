# Third-Party Notices

This project (**Chordz**) is distributed under the MIT License (see `LICENSE`).
It depends on the following third-party software and data. Academic and
dataset citations are kept in `CREDITS.md`.

## librosa — ISC License
A Python package for music and audio analysis. Used for audio I/O, chroma/CQT
feature extraction, and beat tracking.
- Home: https://librosa.org
- License: ISC (permissive; commercial-safe). Copyright the librosa development team.

## numpy — BSD 3-Clause License
Numerical computing foundation. https://numpy.org

## scipy — BSD 3-Clause License
Scientific computing. https://scipy.org

## soundfile — BSD 3-Clause License
Audio file I/O (MP3 support via libsndfile). https://github.com/bastibe/python-soundfile

## audioread — MIT License
Fallback audio decoding backend. https://github.com/beetbox/audioread

## madmom (OPTIONAL — not installed by default)
ML music analysis. Source code: BSD-style (JKU Linz / OFAI). **Model/data
files: CC BY-NC-SA 4.0 (NonCommercial — ShareAlike — Attribution).**
- This package is listed as the optional `[ml]` extra. It is loaded only when the
  user explicitly enables the ML backend and has it installed; it is **not**
  bundled into the default application build.
- Because the models are NonCommercial, any use that relies on them must be
  non-commercial, with attribution to madmom. For commercial use, contact the
  madmom authors or train your own model on permissively-licensed data.
- Home: https://github.com/CPJKU/madmom

## Chordino / NNLS-Chroma (OPTIONAL — not bundled)
An alternative Vamp plugin for chord recognition (Mauch et al., Queen Mary
University of London). Used only if the user installs it separately. See
`CREDITS.md` for the academic citation.

---
This NOTICE file satisfies the attribution requirements of the dependencies
above. If you redistribute Chordz, keep this file and the `LICENSE`.

## Stage 2 (HMM) -- our own numpy code
The HMM chord recognizer in chordz/ml_backend.py is original Chordz code, distributed under the project MIT license (see LICENSE). It depends only on numpy/scipy (already covered above) -- no extra third-party code.

## madmom -- NOT used
madmom was the originally planned Stage 2 backend but is not used or distributed. (Its 2018 release does not install on modern Python/numpy.) The optional path described earlier has been removed in favour of the numpy HMM.

## Demucs / PyTorch (implemented, opt-in, not in the default build)
Optional source-separation preprocessing (Stage 2b) would add Demucs (MIT) and PyTorch (BSD-style), both commercial-safe, loaded only when the user opts in. Not bundled into the default build.

## just_playback (optional -- GUI player audio)
just_playback (miniaudio via cffi) provides audio playback for the Stage 4
player (python -m chordz.player). MIT-licensed, loaded only when the player is
used; not in the default build.

## PyInstaller (build tool only)
PyInstaller (GPLv2 bootloader) builds the Windows .exe. Per the PyInstaller license, the bundled application is not a derivative of PyInstaller -- the frozen chordz.exe stays under the project MIT license. PyInstaller is a build-time tool only; it is not bundled into or required to run the source.
