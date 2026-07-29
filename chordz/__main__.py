"""Chordz launcher (GUI-first).

    chordz                  -> open the GUI (no arguments needed)
    chordz play <audio>     -> open the GUI with <audio> preloaded
    chordz <audio>          -> open the GUI with <audio> preloaded (drag-and-drop)

Headless analysis is still available via:  python -m chordz.cli <audio> [flags]
"""
from __future__ import annotations

import sys
from pathlib import Path

from chordz.player import main as player_main


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return player_main()                       # GUI, no file
    if args[0] == "play":
        return player_main(args[1] if len(args) > 1 else None)
    # Treat the first argument as an audio file to preload (e.g. drag-and-drop
    # onto the .exe). Options live in the GUI now, so extra flags are ignored.
    if Path(args[0]).exists():
        return player_main(args[0])
    return player_main()


if __name__ == "__main__":
    raise SystemExit(main())

