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


def _resource_path(relative_path: str) -> Path:
    """Locate a bundled asset both from source and a PyInstaller executable."""
    import sys

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative_path


def _set_windows_app_id() -> None:
    """Keep Windows from grouping the app under Python's taskbar identity."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Chordz.GuitarLearning")
    except (AttributeError, OSError):
        pass


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

        def __init__(self, master, width=270, height=320, background="#FFFFFF"):
            super().__init__(master, width=width, height=height, bg=background,
                             highlightthickness=0, bd=0)
            self._voicing = None
            self._draw()

        def set_voicing(self, voicing):
            self._voicing = voicing
            self._draw()

        def _draw(self):
            self.delete("all")
            v = self._voicing
            if not v:
                self.create_text(135, 160, text="No chord selected", fill="#8993A7",
                                 font=("Segoe UI", 11))
                return
            frets = v.get("frets", [])
            fingers = v.get("fingers", [])
            name = v.get("name", "")
            left, right, top, bot = 70, 200, 88, 280
            if name:
                self.create_text(135, 33, text=name, fill="#17213A",
                                 font=("Segoe UI", 14, "bold"))
            xs = [left + i * (right - left) / (N_STRINGS - 1) for i in range(N_STRINGS)]
            ys = [top + j * (bot - top) / (N_FRETS - 1) for j in range(N_FRETS)]
            for y in ys:
                self.create_line(left, y, right, y, fill="#C9D1DF", width=1)
            for x in xs:
                self.create_line(x, top, x, bot, fill="#44516A", width=2)
            active = [f for f in frets if f > 0]
            base = 1
            if active and min(active) > 1 and 0 not in frets:
                base = min(active)
            if base <= 1:
                self.create_line(left - 1, top, right + 1, top, fill="#17213A", width=5)  # nut
            else:
                self.create_text(left - 14, (top + ys[1]) / 2, text=f"{base}fr",
                                 fill="#667085", font=("Segoe UI", 9, "bold"))
            for i in range(N_STRINGS):
                f = frets[i] if i < len(frets) else -1
                x = xs[i]
                if f == -1:
                    self.create_text(x, top - 19, text="×", font=("Segoe UI", 13, "bold"),
                                     fill="#E35D6A")
                elif f == 0:
                    self.create_oval(x - 6, top - 25, x + 6, top - 13, outline="#44516A",
                                     width=2)
                else:
                    rel = f - base + 1
                    if 1 <= rel <= N_FRETS - 1:
                        y = (ys[rel - 1] + ys[rel]) / 2
                        self.create_oval(x - 11, y - 11, x + 11, y + 11,
                                         fill="#635BFF", outline="#635BFF")
                        if i < len(fingers) and fingers[i]:
                            self.create_text(x, y, text=str(fingers[i]), fill="white",
                                             font=("Segoe UI", 8, "bold"))


# === APP SECTION ===
class ChordzApp:
    """Unified Chordz GUI: open a file, analyze, then play with synced chords.

    Launch with no file to start empty (use the Analyze rail or Open Audio button);
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
        _set_windows_app_id()
        self.root = tk.Tk()
        self.root.title("Chordz")
        self._set_window_icon()
        self.root.minsize(980, 680)
        self.root.geometry("1180x760")
        self.root.configure(bg="#F5F7FB")
        self._nav_items = []
        self._configure_theme()

        # A wide, app-like shell replaces the old stacked controls while keeping
        # the same analysis and playback widgets available to the callbacks below.
        shell = tk.Frame(self.root, bg="#F5F7FB")
        shell.pack(fill="both", expand=True)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(shell, bg="#151A2D", width=244)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        main = tk.Frame(shell, bg="#F5F7FB")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        header = tk.Frame(main, bg="#F5F7FB")
        header.grid(row=0, column=0, sticky="ew", padx=34, pady=(28, 20))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="YOUR GUITAR PRACTICE SPACE", bg="#F5F7FB", fg="#7A8499",
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(header, text="Learn songs one chord at a time.", bg="#F5F7FB", fg="#17213A",
                 font=("Segoe UI", 24, "bold")).grid(row=1, column=0, sticky="w", pady=(3, 0))
        self._make_button(header, "＋  Choose a song", self.open_file, primary=True).grid(
            row=0, column=1, rowspan=2, sticky="e")

        workspace = tk.Frame(main, bg="#F5F7FB")
        workspace.grid(row=1, column=0, sticky="nsew", padx=34, pady=(0, 30))
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_columnconfigure(1, minsize=322)
        workspace.grid_rowconfigure(0, weight=1)

        # Current chord card
        player_card = self._card(workspace)
        player_card.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        player_card.grid_columnconfigure(0, weight=1)
        player_card.grid_rowconfigure(3, weight=1)
        top_line = tk.Frame(player_card, bg="#FFFFFF")
        top_line.grid(row=0, column=0, sticky="ew", padx=26, pady=(24, 0))
        top_line.grid_columnconfigure(0, weight=1)
        self.track_badge = tk.Label(top_line, text="READY WHEN YOU ARE", bg="#EEF0FF", fg="#635BFF",
                                    font=("Segoe UI", 9, "bold"), padx=10, pady=5)
        self.track_badge.grid(row=0, column=0, sticky="w")
        self.status = tk.Label(top_line, text="Choose a song to begin", bg="#FFFFFF", fg="#7A8499",
                               font=("Segoe UI", 10), anchor="e")
        self.status.grid(row=0, column=1, sticky="e")
        self.track_name = tk.Label(player_card, text="Pick a favorite song", bg="#FFFFFF",
                                   fg="#17213A", font=("Segoe UI", 17, "bold"), anchor="w")
        self.track_name.grid(row=1, column=0, sticky="ew", padx=26, pady=(16, 2))
        self.track_hint = tk.Label(player_card, text="Chordz finds the chords, then lets you learn along at your own pace.",
                                   bg="#FFFFFF", fg="#7A8499", font=("Segoe UI", 10), anchor="w")
        self.track_hint.grid(row=2, column=0, sticky="ew", padx=26)
        hero = tk.Frame(player_card, bg="#FFFFFF")
        hero.grid(row=3, column=0, sticky="nsew")
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_rowconfigure(0, weight=1)
        self.symbol = tk.Label(hero, text="—", bg="#FFFFFF", fg="#17213A",
                               font=("Segoe UI", 68, "bold"))
        self.symbol.grid(row=0, column=0, pady=(10, 0))
        tk.Label(hero, text="YOUR NEXT CHORD", bg="#FFFFFF", fg="#A0A8B8",
                 font=("Segoe UI", 9, "bold")).grid(row=1, column=0, pady=(0, 16))

        # Playback is a single, prominent strip beneath the now-playing card.
        playback = self._card(player_card, background="#F9FAFE", border="#E4E9F3")
        playback.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 18))
        playback.grid_columnconfigure(1, weight=1)
        self.play_btn = self._make_button(playback, "▶  Play", self._toggle_play, primary=True)
        self.play_btn.grid(row=0, column=0, rowspan=2, padx=(16, 14), pady=16, sticky="ns")
        self.scrub = ttk.Scale(playback, from_=0, to=1.0, command=self._on_scrub,
                               style="Chordz.Horizontal.TScale")
        self.scrub.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 16), pady=(17, 7))
        self.time_lbl = tk.Label(playback, text="0:00  /  0:00", bg="#F9FAFE", fg="#5D687D",
                                 font=("Segoe UI", 10, "bold"))
        self.time_lbl.grid(row=1, column=1, sticky="w", padx=(0, 12), pady=(0, 16))
        speed_area = tk.Frame(playback, bg="#F9FAFE")
        speed_area.grid(row=1, column=2, sticky="e", padx=(0, 16), pady=(0, 12))
        tk.Label(speed_area, text="SPEED", bg="#F9FAFE", fg="#929BAE",
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 7))
        self.speed_var = tk.StringVar(value="1.00x")
        self.speed_box = ttk.Combobox(speed_area, textvariable=self.speed_var,
                                      values=["1.00x", "0.85x", "0.75x", "0.65x", "0.50x"],
                                      width=6, state="readonly", style="Chordz.TCombobox")
        self.speed_box.pack(side="left")
        self.speed_box.bind("<<ComboboxSelected>>", self._on_speed)

        # A dedicated card gives the voicing the space it needs instead of
        # treating it as a small afterthought below the controls.
        voicing_card = self._card(workspace)
        voicing_card.grid(row=0, column=1, sticky="nsew")
        tk.Label(voicing_card, text="How to play it", bg="#FFFFFF", fg="#17213A",
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=24, pady=(24, 2))
        tk.Label(voicing_card, text="Suggested guitar fingering", bg="#FFFFFF", fg="#7A8499",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=24)
        self.diagram = ChordDiagram(voicing_card, background="#FFFFFF")
        self.diagram.pack(padx=22, pady=(8, 2))
        tk.Label(voicing_card, text="The chord shape updates while the song plays.", bg="#FFFFFF", fg="#8D97AA",
                 font=("Segoe UI", 9)).pack(padx=24, pady=(0, 12))

        options = self._card(main, background="#FFFFFF")
        options.grid(row=2, column=0, sticky="ew", padx=34, pady=(0, 28))
        options.grid_columnconfigure(4, weight=1)
        tk.Label(options, text="Practice options", bg="#FFFFFF", fg="#17213A",
                 font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=22, pady=(17, 4))
        tk.Label(options, text="Choose how you want Chordz to prepare the song.", bg="#FFFFFF", fg="#7A8499",
                 font=("Segoe UI", 9)).grid(row=1, column=0, columnspan=2, sticky="w", padx=22, pady=(0, 17))
        self.ml_var = tk.BooleanVar(value=True)
        self.sep_var = tk.BooleanVar(value=False)
        self._make_checkbutton(options, "Smooth chord changes", self.ml_var).grid(
            row=0, column=2, rowspan=2, padx=(18, 8), pady=10)
        self._make_checkbutton(options, "Focus on instruments", self.sep_var).grid(
            row=0, column=3, rowspan=2, padx=8, pady=10)
        device_area = tk.Frame(options, bg="#FFFFFF")
        device_area.grid(row=0, column=4, rowspan=2, sticky="e", padx=22, pady=10)
        tk.Label(device_area, text="ANALYSIS ENGINE", bg="#FFFFFF", fg="#929BAE",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.device_var = tk.StringVar(value="auto")
        self.device_box = ttk.Combobox(device_area, textvariable=self.device_var,
                                       values=["auto", "cuda", "xpu", "cpu"], width=8,
                                       state="readonly", style="Chordz.TCombobox")
        self.device_box.pack(anchor="w", pady=(3, 0))

        self._set_loaded(False)
        self._set_active_nav(self._analyze_nav)
        self.root.bind("<Control-o>", lambda _event: self.open_file())
        self.root.after(40, self._tick)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        if audio_path:
            self._load_file(str(audio_path), json_path)

    def _configure_theme(self):
        """Apply a restrained, high-contrast theme to Tk's native controls."""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Chordz.TCombobox", fieldbackground="#FFFFFF", background="#FFFFFF",
                        foreground="#17213A", bordercolor="#DCE2EE", lightcolor="#DCE2EE",
                        darkcolor="#DCE2EE", padding=(8, 7), arrowsize=13)
        style.map("Chordz.TCombobox", fieldbackground=[("disabled", "#F0F3F8")],
                  foreground=[("disabled", "#9BA4B5")])
        style.configure("Chordz.Horizontal.TScale", background="#F9FAFE", troughcolor="#DDE4F0",
                        sliderlength=20, borderwidth=0)

    def _set_window_icon(self):
        """Use the Chordz mark in the title bar and Windows taskbar."""
        icon_path = _resource_path("data/chordz.ico")
        if not icon_path.exists():
            return
        try:
            self.root.iconbitmap(str(icon_path))
        except tk.TclError:
            pass

    @staticmethod
    def _card(parent, background="#FFFFFF", border="#E7EBF3"):
        return tk.Frame(parent, bg=background, highlightbackground=border,
                        highlightthickness=1, bd=0)

    @staticmethod
    def _make_button(parent, text, command, primary=False):
        if primary:
            colors = {"bg": "#635BFF", "fg": "#FFFFFF", "activebackground": "#5148E5"}
        else:
            colors = {"bg": "#ECEEFF", "fg": "#4D46C5", "activebackground": "#DFE1FF"}
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
                         padx=16, pady=10, cursor="hand2", font=("Segoe UI", 10, "bold"),
                         activeforeground=colors["fg"], disabledforeground="#AAB1C1", **colors)

    @staticmethod
    def _make_checkbutton(parent, text, variable):
        return tk.Checkbutton(parent, text=text, variable=variable, bg="#FFFFFF", fg="#44516A",
                              activebackground="#FFFFFF", activeforeground="#17213A",
                              selectcolor="#FFFFFF", font=("Segoe UI", 10), cursor="hand2",
                              highlightthickness=0, bd=0)

    def _build_sidebar(self, sidebar):
        brand = tk.Frame(sidebar, bg="#151A2D")
        brand.pack(fill="x", padx=22, pady=(30, 30))
        mark = tk.Canvas(brand, width=42, height=42, bg="#151A2D", highlightthickness=0)
        mark.pack(side="left")
        mark.create_oval(2, 2, 40, 40, fill="#635BFF", outline="")
        mark.create_text(21, 20, text="♬", fill="#FFFFFF", font=("Segoe UI Symbol", 20, "bold"))
        name = tk.Frame(brand, bg="#151A2D")
        name.pack(side="left", padx=11)
        tk.Label(name, text="Chordz", bg="#151A2D", fg="#FFFFFF",
                 font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(name, text="LEARN YOUR FAVORITE SONGS", bg="#151A2D", fg="#838CA6",
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")

        tk.Label(sidebar, text="YOUR LESSON", bg="#151A2D", fg="#7C86A0",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=24, pady=(0, 8))
        self._analyze_nav = self._add_nav_item(sidebar, "♫", "Choose a song", "Find the chords to learn", self.open_file)
        self._player_nav = self._add_nav_item(sidebar, "▶", "Play along", "Follow each chord in time", self._focus_player)
        self._settings_nav = self._add_nav_item(sidebar, "⚙", "Practice options", "Make the lesson yours", self._focus_settings)

        spacer = tk.Frame(sidebar, bg="#151A2D")
        spacer.pack(fill="both", expand=True)
        footer = tk.Frame(sidebar, bg="#202741")
        footer.pack(fill="x", padx=15, pady=18)
        tk.Label(footer, text="PRACTICE TIP", bg="#202741", fg="#AAB4CF",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=13, pady=(11, 1))
        tk.Label(footer, text="Start slowly, then build up to full speed.", bg="#202741", fg="#EEF1FA",
                 font=("Segoe UI", 9), wraplength=180, justify="left").pack(anchor="w", padx=13, pady=(0, 11))

    def _add_nav_item(self, parent, icon, title, subtitle, command):
        item = tk.Frame(parent, bg="#151A2D", height=70, cursor="hand2")
        item.pack(fill="x", padx=14, pady=3)
        item.pack_propagate(False)
        item.grid_columnconfigure(2, weight=1)
        accent = tk.Frame(item, bg="#151A2D", width=4)
        accent.grid(row=0, column=0, rowspan=2, sticky="ns")
        badge = tk.Label(item, text=icon, bg="#202741", fg="#D9DEFF",
                         font=("Segoe UI Symbol", 21), width=2)
        badge.grid(row=0, column=1, rowspan=2, padx=(14, 10), pady=12)
        title_label = tk.Label(item, text=title, bg="#151A2D", fg="#FFFFFF",
                               font=("Segoe UI", 11, "bold"), anchor="w")
        title_label.grid(row=0, column=2, sticky="sw", pady=(12, 0))
        subtitle_label = tk.Label(item, text=subtitle, bg="#151A2D", fg="#8490AB",
                                  font=("Segoe UI", 8), anchor="w")
        subtitle_label.grid(row=1, column=2, sticky="nw", pady=(0, 11))
        entry = {"frame": item, "accent": accent, "badge": badge, "title": title_label,
                 "subtitle": subtitle_label}
        self._nav_items.append(entry)

        def activate(_event=None):
            self._set_active_nav(entry)
            command()

        def hover(on):
            if entry.get("active"):
                return
            color = "#1C223A" if on else "#151A2D"
            for widget in (item, accent, title_label, subtitle_label):
                widget.configure(bg=color)
            badge.configure(bg="#2A3150" if on else "#202741")

        for widget in (item, accent, badge, title_label, subtitle_label):
            widget.bind("<Button-1>", activate)
            widget.bind("<Enter>", lambda _event: hover(True))
            widget.bind("<Leave>", lambda _event: hover(False))
        return entry

    def _set_active_nav(self, selected):
        for entry in self._nav_items:
            active = entry is selected
            entry["active"] = active
            color = "#222A49" if active else "#151A2D"
            for widget in (entry["frame"], entry["title"], entry["subtitle"]):
                widget.configure(bg=color)
            entry["accent"].configure(bg="#8B84FF" if active else color)
            entry["badge"].configure(bg="#635BFF" if active else "#202741",
                                     fg="#FFFFFF" if active else "#D9DEFF")

    def _focus_player(self):
        if self.timeline is not None:
            self.scrub.focus_set()

    def _focus_settings(self):
        self.device_box.focus_set()

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
        self.track_badge.config(text="FINDING CHORDS", bg="#FFF3D9", fg="#B76A00")
        self.track_name.config(text=self._audio_path.name)
        self.track_hint.config(text="Listening for the chord changes in this song…")
        self.status.config(text=f"Finding the chords in {self._audio_path.name}…")
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
            self.track_badge.config(text="LET'S TRY AGAIN", bg="#FFE8EB", fg="#C2384A")
            self.track_hint.config(text="Try another song or adjust the practice options.")
            self.status.config(text=f"We couldn't read this song: {holder['err'][:80]}")
            return
        try:
            with open(holder["ok"], "r", encoding="utf-8") as f:
                self.timeline = json.load(f)
        except Exception as e:
            self.track_badge.config(text="LET'S TRY AGAIN", bg="#FFE8EB", fg="#C2384A")
            self.status.config(text=f"We couldn't prepare the chord guide: {e}")
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
        self.track_badge.config(text="READY TO PLAY", bg="#E4F8EF", fg="#16734D")
        self.track_hint.config(text="Your chord guide is ready — press Play and learn along.")
        self._set_active_nav(self._player_nav)
        if self.audio is None:
            self.play_btn.config(state="disabled")
            self.status.config(text=self._audio_err or "You can still move the timeline to see each chord.")
        else:
            self.status.config(text="Your song is ready to play.")
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
        self.play_btn.config(text="▶  Play")

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
            self.audio.pause(); self._playing = False; self.play_btn.config(text="▶  Play")
        else:
            if not self.audio.active:
                self.audio.play()
            else:
                self.audio.resume()
            self._playing = True; self.play_btn.config(text="Ⅱ  Pause")

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
                self.status.config(text=f"Couldn't change the practice speed ({e})")
                return
            self.status.config(text="Your song is ready to play.")
            if was_playing:
                try:
                    self.audio.play()
                    self.audio.seek(pos_orig / speed)
                except Exception:
                    pass
                self._playing = True
                self.play_btn.config(text="Ⅱ  Pause")
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
            self.play_btn.config(text="▶  Play")
        self.root.after(40, self._tick)

    def _update_display(self, t):
        seg = find_segment(self.timeline, t) if self.timeline else None
        self.symbol.config(text=(seg["symbol"] if seg else "N"))
        self.time_lbl.config(text=f"{self._format_time(t)}  /  {self._format_time(self.duration)}")
        self.diagram.set_voicing((seg.get("voicings") or [None])[0] if seg else None)

    @staticmethod
    def _format_time(seconds):
        seconds = max(0, int(seconds))
        return f"{seconds // 60}:{seconds % 60:02d}"

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
