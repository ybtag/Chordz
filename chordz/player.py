"""Stage 4: graphical chord display synced to playback (Tkinter).

Loads an audio file and its ``*.chordz.json`` timeline, plays the audio, and
shows the active chord symbol + a guitar chord diagram, advancing in sync with
playback. Audio uses ``just_playback`` (MIT) if installed; otherwise the app
runs without audio (drag the scrub bar to step through the chords).

Run:  python -m chordz.player path/to/song.mp3
"""
from __future__ import annotations

import json
from bisect import bisect_right
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # headless / no tkinter build
    tk = None


def find_segment(timeline: dict, t: float) -> dict | None:
    """Return the segment active at time ``t`` (the last with start <= t)."""
    segs = timeline.get("segments", []) if isinstance(timeline, dict) else []
    if not segs:
        return None
    starts = [s["start"] for s in segs]
    i = bisect_right(starts, t) - 1
    return segs[i] if i >= 0 else segs[0]


def _audio_backend():
    """Return (just_playback.Playback or None, reason str or None)."""
    try:
        from just_playback import Playback
        return Playback(), None
    except Exception as e:
        return None, f"just_playback not available ({e})"


def map_to_original_time(t_slowed: float, speed: float) -> float:
    """Map a position in slowed audio back to original-song time.

    A song played at ``speed`` (e.g. 0.5 = half speed) is ``1/speed`` times
    longer, so a playback position in the slowed file maps to original time by
    multiplying by ``speed``.
    """
    return t_slowed * speed


def prepare_slowed_audio(audio_path: str, speed: float, cache: dict | None = None) -> str:
    """Return a path to a WAV of the song at the given playback speed.

    ``speed=1.0`` returns the original path. ``speed<1`` slows the audio down
    (``speed>1`` speeds it up) using a phase vocoder, which preserves pitch so
    the detected chords still match. Slowed copies are cached per speed.
    """
    if speed == 1.0:
        return str(audio_path)
    cache = cache if cache is not None else {}
    key = (str(audio_path), speed)
    cached = cache.get(key)
    if cached and Path(cached).exists():
        return cached
    import os
    import tempfile

    import librosa
    import soundfile as sf

    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    y2 = librosa.effects.time_stretch(y, rate=speed)
    fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="chordz_slow_")
    os.close(fd)
    sf.write(tmp, y2, sr)
    cache[key] = tmp
    return tmp


if tk is not None:
    N_STRINGS = 6
    N_FRETS = 5

    class ChordDiagram(tk.Canvas):
        """A small canvas that draws a guitar chord diagram from a voicing."""

        def __init__(self, master, width=220, height=260):
            super().__init__(master, width=width, height=height, bg="white",
                             highlightthickness=0)
            self._voicing = None
            self._draw()

        def set_voicing(self, voicing):
            self._voicing = voicing
            self._draw()

        def _draw(self):
            self.delete("all")
            v = self._voicing
            if not v:
                self.create_text(110, 130, text="(no chord)", fill="#999")
                return
            frets = v.get("frets", [])
            fingers = v.get("fingers", [])
            name = v.get("name", "")
            left, right, top, bot = 60, 160, 70, 230
            if name:
                self.create_text(110, 24, text=name, font=("Arial", 11, "bold"))
            xs = [left + i * (right - left) / (N_STRINGS - 1) for i in range(N_STRINGS)]
            ys = [top + j * (bot - top) / (N_FRETS - 1) for j in range(N_FRETS)]
            for y in ys:
                self.create_line(left, y, right, y, fill="#ccc")
            for x in xs:
                self.create_line(x, top, x, bot, fill="#444")
            active = [f for f in frets if f > 0]
            base = 1
            if active and min(active) > 1 and 0 not in frets:
                base = min(active)
            if base <= 1:
                self.create_line(left - 1, top, right + 1, top, width=4)  # nut
            else:
                self.create_text(left - 14, (top + ys[1]) / 2, text=f"{base}fr",
                                 font=("Arial", 9))
            for i in range(N_STRINGS):
                f = frets[i] if i < len(frets) else -1
                x = xs[i]
                if f == -1:
                    self.create_text(x, top - 14, text="X", font=("Arial", 10, "bold"),
                                     fill="#a33")
                elif f == 0:
                    self.create_oval(x - 5, top - 19, x + 5, top - 9, outline="#333")
                else:
                    rel = f - base + 1
                    if 1 <= rel <= N_FRETS - 1:
                        y = (ys[rel - 1] + ys[rel]) / 2
                        self.create_oval(x - 9, y - 9, x + 9, y + 9, fill="#335", outline="#335")
                        if i < len(fingers) and fingers[i]:
                            self.create_text(x, y, text=str(fingers[i]), fill="white",
                                             font=("Arial", 8, "bold"))


# === APP SECTION ===
class ChordzApp:
    """Unified Chordz GUI: open a file, analyze, then play with synced chords.

    Launch with no file to start empty (use File > Open or the Open button);
    pass an audio path to preload it. All options (HMM, stem separation, device,
    playback speed) are in the window -- no command-line flags required.
    """

    AUDIO_EXTS = [("Audio", "*.mp3 *.wav *.ogg *.flac *.m4a *.aac"), ("All files", "*.*")]

    def __init__(self, audio_path=None, json_path=None):
        if tk is None:
            raise RuntimeError("tkinter is not available on this system")
        # state
        self.timeline = None
        self.duration = 0.0
        self._audio_path = None
        self.speed = 1.0
        self._slow_cache: dict = {}
        self.audio, self._audio_err = _audio_backend()
        self._playing = False
        self.root = tk.Tk()
        self.root.title("Chordz")
        self.root.minsize(360, 540)
        # menu bar
        menubar = tk.Menu(self.root)
        m = tk.Menu(menubar, tearoff=0)
        m.add_command(label="Open audio…", command=self.open_file)
        m.add_separator()
        m.add_command(label="Exit", command=self._close)
        menubar.add_cascade(label="File", menu=m)
        self.root.config(menu=menubar)
        # options row
        opt = tk.Frame(self.root)
        opt.pack(fill="x", padx=12, pady=(8, 2))
        self.ml_var = tk.BooleanVar(value=True)
        self.sep_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="HMM", variable=self.ml_var).pack(side="left")
        ttk.Checkbutton(opt, text="Separate", variable=self.sep_var).pack(side="left", padx=(4, 0))
        tk.Label(opt, text="Device:").pack(side="left", padx=(10, 2))
        self.device_var = tk.StringVar(value="auto")
        ttk.Combobox(opt, textvariable=self.device_var,
                     values=["auto", "cuda", "xpu", "cpu"], width=6, state="readonly").pack(side="left")
        # open button + status
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=12, pady=4)
        ttk.Button(top, text="Open Audio File…", command=self.open_file).pack(side="left")
        self.status = tk.Label(top, text="no file loaded", font=("Arial", 9), fg="#555", anchor="w")
        self.status.pack(side="left", padx=10, fill="x", expand=True)
        # player area (disabled until a file is loaded)
        self.symbol = tk.Label(self.root, text="—", font=("Arial", 30, "bold"))
        self.symbol.pack(pady=(8, 0))
        self.time_lbl = tk.Label(self.root, text="0.0 / 0.0 s", font=("Arial", 10))
        self.time_lbl.pack()
        self.diagram = ChordDiagram(self.root)
        self.diagram.pack(padx=10, pady=8)
        self.scrub = ttk.Scale(self.root, from_=0, to=1.0, command=self._on_scrub)
        self.scrub.pack(fill="x", padx=20)
        ctrl = tk.Frame(self.root)
        ctrl.pack(pady=8)
        self.play_btn = ttk.Button(ctrl, text="Play", command=self._toggle_play)
        self.play_btn.pack(side="left", padx=4)
        tk.Label(ctrl, text="Speed:").pack(side="left", padx=(8, 2))
        self.speed_var = tk.StringVar(value="1.00x")
        self.speed_box = ttk.Combobox(ctrl, textvariable=self.speed_var,
                                      values=["1.00x", "0.85x", "0.75x", "0.65x", "0.50x"],
                                      width=6, state="readonly")
        self.speed_box.pack(side="left")
        self.speed_box.bind("<<ComboboxSelected>>", self._on_speed)
        self._set_loaded(False)
        self.root.after(40, self._tick)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        if audio_path:
            self._load_file(str(audio_path), json_path)

    # --- file loading / analysis (background thread keeps the UI responsive) ---
    def open_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(title="Open audio file", filetypes=self.AUDIO_EXTS)
        if path:
            self._load_file(path)

    def _load_file(self, path, json_path=None):
        import threading
        self._stop_audio()
        self._clear_slow_cache()
        self._set_loaded(False)
        self._audio_path = Path(path)
        jp = Path(json_path) if json_path else self._audio_path.with_suffix(".chordz.json")
        self.status.config(text=f"Analyzing {self._audio_path.name}…")
        use_ml, separate, device = self.ml_var.get(), self.sep_var.get(), self.device_var.get()
        holder: dict = {}

        def worker():
            try:
                from chordz.cli import analyze
                from chordz.renderers.json_out import render_json_file
                tl = analyze(str(self._audio_path), use_ml=use_ml, separate=separate, device=device)
                render_json_file(tl, str(jp))
                holder["ok"] = str(jp)
            except Exception as e:
                holder["err"] = str(e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        self._poll_analysis(t, holder)

    def _poll_analysis(self, thread, holder):
        if thread.is_alive():
            self.root.after(100, lambda: self._poll_analysis(thread, holder))
        else:
            self._on_analyzed(holder)

    def _on_analyzed(self, holder):
        if "err" in holder:
            self.status.config(text=f"analysis failed: {holder['err'][:80]}")
            return
        try:
            with open(holder["ok"], "r", encoding="utf-8") as f:
                self.timeline = json.load(f)
        except Exception as e:
            self.status.config(text=f"failed to read timeline: {e}")
            return
        self.duration = float(self.timeline.get("audio", {}).get("duration", 0.0) or 0.0)
        self.speed = 1.0
        self.speed_var.set("1.00x")
        if self.audio is not None:
            try:
                self.audio.load_file(str(self._audio_path))
            except Exception as e:
                self.audio = None
                self._audio_err = f"could not load audio ({e})"
        self.scrub.config(to=max(self.duration, 0.001))
        self._set_loaded(True)
        if self.audio is None:
            self.play_btn.config(state="disabled")
            self.status.config(text=self._audio_err or "no audio backend (scrub only)")
        else:
            self.status.config(text="ready")
        self._update_display(0.0)

    def _set_loaded(self, loaded):
        state = "normal" if loaded else "disabled"
        self.play_btn.config(state=state)
        self.scrub.config(state=state)
        self.speed_box.config(state="readonly" if loaded else "disabled")

    def _stop_audio(self):
        if self.audio is not None:
            try:
                self.audio.stop()
            except Exception:
                pass
        self._playing = False
        self.play_btn.config(text="Play")

    def _clear_slow_cache(self):
        for p in self._slow_cache.values():
            try:
                if p and "chordz_slow_" in str(p) and Path(p).exists():
                    Path(p).unlink()
            except Exception:
                pass
        self._slow_cache = {}

    def _toggle_play(self):
        if self.audio is None or self.timeline is None:
            return
        if self._playing:
            self.audio.pause(); self._playing = False; self.play_btn.config(text="Play")
        else:
            if not self.audio.active:
                self.audio.play()
            else:
                self.audio.resume()
            self._playing = True; self.play_btn.config(text="Pause")

    def _on_speed(self, _evt=None):
        if self.timeline is None:
            return
        try:
            speed = float(self.speed_var.get().rstrip("x"))
        except ValueError:
            return
        if speed <= 0 or speed == self.speed:
            return
        was_playing = self._playing
        pos_orig = 0.0
        if self.audio is not None and self.audio.active:
            try:
                pos_orig = map_to_original_time(float(self.audio.curr_pos), self.speed)
            except Exception:
                pos_orig = 0.0
            self._stop_audio()
        self.speed = speed
        if self.audio is not None:
            try:
                slowed = prepare_slowed_audio(str(self._audio_path), speed, self._slow_cache)
                self.audio.load_file(slowed)
            except Exception as e:
                self.status.config(text=f"speed render failed ({e})")
                return
            self.status.config(text="ready")
            if was_playing:
                try:
                    self.audio.play()
                    self.audio.seek(pos_orig / speed)
                except Exception:
                    pass
                self._playing = True
                self.play_btn.config(text="Pause")
        self.scrub.set(pos_orig)
        self._update_display(pos_orig)

    def _on_scrub(self, val):
        if self.timeline is None:
            return
        t = float(val)
        if self.audio is not None and self.audio.active:
            try:
                self.audio.seek(t / self.speed)
            except Exception:
                pass
        self._update_display(t)

    def _tick(self):
        if self.audio is not None and self.timeline is not None and self.audio.active:
            try:
                t_slow = float(self.audio.curr_pos)
            except Exception:
                t_slow = 0.0
            t = map_to_original_time(t_slow, self.speed)
            self.scrub.set(t)
            self._update_display(t)
        elif self._playing:
            self._playing = False
            self.play_btn.config(text="Play")
        self.root.after(40, self._tick)

    def _update_display(self, t):
        seg = find_segment(self.timeline, t) if self.timeline else None
        self.symbol.config(text=(seg["symbol"] if seg else "N"))
        self.time_lbl.config(text=f"{t:.1f} / {self.duration:.1f} s")
        self.diagram.set_voicing((seg.get("voicings") or [None])[0] if seg else None)

    def _close(self):
        self._stop_audio()
        self._clear_slow_cache()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def _close_packaged_splash() -> None:
    """Close PyInstaller's early splash once the real window is ready."""
    try:
        import pyi_splash
    except ImportError:
        return
    try:
        if pyi_splash.is_alive():
            pyi_splash.close()
    except (ConnectionError, OSError, RuntimeError):
        pass


def main(audio: str | None = None, json_path: str | None = None) -> int:
    app = ChordzApp(audio_path=audio, json_path=json_path)
    app.root.update_idletasks()
    _close_packaged_splash()
    app.run()
    return 0


if __name__ == "__main__":
    import sys
    audio = sys.argv[1] if len(sys.argv) > 1 else None
    jp = sys.argv[2] if len(sys.argv) > 2 else None
    raise SystemExit(main(audio, jp))
