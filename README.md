# Chordz

Local MP3 → guitar chord analysis. Analyzes an audio file and outputs a
time-aligned sequence of guitar chords (symbols + fingerings), fully offline.

Chordz runs entirely on your machine — no cloud, no API keys. Stage 1 uses
classical signal processing (librosa chroma + beat tracking + template
matching). Stage 2 adds a numpy-only HMM chord recognizer (Krumhansl key
estimation + Viterbi smoothing) via `--ml` — no extra dependencies. Stage 2b
adds optional Demucs source separation via `--separate` (isolates the harmonic
accompaniment, excluding vocals/drums) to boost real-mix accuracy; it pulls
PyTorch and is **not** bundled into the default build (see Licensing).

## Status
- [x] Stage 1 — librosa + template matching (this release)
- [x] Stage 2 — HMM chord recognizer (numpy; `--ml`)
- [x] Stage 2b — optional Demucs source separation (`--separate`)
- [x] Stage 3 — guitar voicing / voice-leading refinement
- [x] Stage 4 — graphical chord display synced to playback
- [x] Stage 5 — Windows .exe packaging (PyInstaller)

## Install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -e .[dev]
```

Requires Python 3.10+.

## Usage

```bash
chordz path/to/song.mp3                  # analyze: print chords, write song.chordz.json
chordz song.mp3 --text song.chords.txt   # also write a text chord sheet
chordz song.mp3 --ml                     # Stage 2 HMM backend (recommended)
chordz song.mp3 --separate --ml          # Demucs stems first (needs the [demucs] extra)
chordz song.mp3 --separate --ml --device xpu   # force Intel GPU for Demucs
chordz play song.mp3                     # open the graphical player (auto-analyzes if needed)
```

In the player, a **Speed** dropdown slows playback (1.00x / 0.85x / 0.75x /
0.65x / 0.50x) **without changing pitch** — so the chords still match. Useful
for learning fast changes. Slowed audio is rendered once per speed (cached) and
the chord timeline stays in sync with the slowed playback.

The `*.chordz.json` file is the canonical artifact: a time-aligned chord
timeline the graphical player consumes. The player needs the `[gui]` extra
(`pip install -e .[gui]`) for audio; otherwise it runs scrub-only.

## Packaging (Windows .exe)

```bash
build_exe.bat        # produces dist\chordz.exe (~140 MB, light build)
```

The light build (librosa + HMM + player) is fully self-contained and uses only
permissive licenses. The optional `[demucs]`/torch runtime is **excluded** from
the default build (run it from source for `--separate`, or build a heavy
variant that drops the `--exclude-module torch` lines).

## Architecture

```
audio -> [optional: Demucs -> 'other'+'bass' stems] -> chroma(CQT) -> beats ->
         [HMM (--ml) | template matching] -> voicings (movable + voice-leading) ->
         timeline -> renderers (text + JSON + graphical player)
```

## Licensing

- **Chordz code**: MIT (see `LICENSE`).
- **librosa**: ISC; **numpy/scipy/soundfile**: BSD; **just_playback**: MIT — all permissive.
- **Demucs** (optional `[demucs]` extra, `--separate`): MIT; pulls PyTorch (BSD-style). Not in the default build/exe.
- **PyInstaller** (build tool only): GPLv2 bootloader; per its license the frozen `chordz.exe` stays MIT.

No non-commercial (NC) dependencies. See `NOTICE.md` and `CREDITS.md`.

## Credits

This project builds on librosa (McFee et al., 2015) and the broader Music
Information Retrieval community. See `CREDITS.md` for citations.

---

Stage 2 (HMM chord recognizer via the --ml flag) is implemented and validated on the progression and the Sweet Waltz piano sample.

Vibe coded with GLM 5.2.
