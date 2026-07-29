# Chordz

Chordz is a desktop app that listens to a song and follows along with guitar
chords. As the song plays, it shows the current chord name and a fingering
diagram. The audio stays on your computer and is analyzed locally.

## Using Chordz

1. Open Chordz.
2. Choose **Open Audio File…** or select **File > Open audio…**.
3. Pick a song and wait for the status to change from **Analyzing…** to
   **ready**.
4. Press **Play**. The chord name and diagram will update with the music.

Chordz accepts MP3, WAV, OGG, FLAC, M4A, and AAC files. You can also drag an
audio file onto the Chordz app to open it directly.

## The Chordz window

- **HMM** smooths the analysis by considering the musical context around each
  chord. It is enabled by default.
- **Separate** tries to remove vocals and drums before detecting chords. This
  can help with busy recordings, but takes longer and requires a copy of Chordz
  that includes source-separation support.
- **Device** chooses the processor used for source separation. **Auto** is the
  best choice for most computers; CUDA, XPU, and CPU are available when a
  specific device is needed.
- The large chord name and fingering diagram show what to play at the current
  point in the song. Muted strings, open strings, fret positions, and finger
  numbers are included in the diagram.
- The timeline can be dragged to move to another part of the song.
- **Play/Pause** controls playback.
- **Speed** slows playback to 0.85x, 0.75x, 0.65x, or 0.50x without changing
  pitch, so the detected chords remain in sync.

Choose the analysis options before opening a song. To analyze it with different
settings, change the options and open the file again. The first use of a slower
playback speed may take a moment while Chordz prepares the audio.

## Saved analysis

Chordz saves the chord timing data beside the song as a `.chordz.json` file.
For example, analyzing `song.mp3` creates `song.chordz.json`. The original
audio file is not changed.

Chord detection is an estimate. Clear recordings with distinct harmonic
instruments usually give the best results, while dense mixes, unusual tunings,
and extended chords can be more difficult.

## License and credits

Chordz is released under the [MIT License](LICENSE). Third-party license
details are listed in [NOTICE.md](NOTICE.md), and project credits and citations
are in [CREDITS.md](CREDITS.md).
