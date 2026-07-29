"""Guitar chord voicings: symbol -> fingerings + voice-leading (Stage 3).

Stage 1 attached the first known open shape. Stage 3 adds:
- movable barre generation for maj/min/7/maj7/min7 (E-shape + A-shape families)
  so every detected chord has at least one playable voicing;
- a voice-leading heuristic that, given the previous chord's chosen voicing,
  picks the candidate minimizing hand movement (fret-position distance), with a
  mild preference for low/open shapes. Diminished triads get no generated
  voicing (the symbol is still shown).
"""
from __future__ import annotations

import json
from pathlib import Path

from .chords import PITCH_CLASSES

DEFAULT_SHAPES_PATH = Path(__file__).resolve().parent / "data" / "chord_shapes.json"

# Standard tuning, low -> high: E A D G B E. Fret arrays follow this order;
# -1 = muted, 0 = open.

# Movable barre templates: relative frets (low->high; -1 = mute) and fingers,
# for the E-shape (root on 6th string) and A-shape (root on 5th string). Add
# the barre fret n to every non-muted fret.
_E_SHAPE = {
    "maj":  ((0, 2, 2, 1, 0, 0), (1, 3, 4, 2, 1, 1)),
    "min":  ((0, 2, 2, 0, 0, 0), (1, 3, 4, 1, 1, 1)),
    "7":    ((0, 2, 0, 1, 0, 0), (1, 3, 0, 2, 1, 1)),
    "maj7": ((0, 2, 1, 1, 0, 0), (1, 3, 2, 2, 1, 1)),
    "min7": ((0, 2, 0, 0, 0, 0), (1, 3, 0, 1, 1, 1)),
}
_A_SHAPE = {
    "maj":  ((-1, 0, 2, 2, 2, 0), (0, 1, 2, 3, 4, 1)),
    "min":  ((-1, 0, 2, 2, 1, 0), (0, 1, 2, 3, 4, 1)),
    "7":    ((-1, 0, 2, 0, 2, 0), (0, 1, 2, 0, 3, 1)),
    "maj7": ((-1, 0, 2, 1, 2, 0), (0, 1, 2, 1, 3, 1)),
    "min7": ((-1, 0, 2, 0, 1, 0), (0, 1, 2, 0, 3, 1)),
}
_SUFFIX = {"maj": "", "min": "m", "7": "7", "maj7": "maj7", "min7": "m7"}


def load_shapes(path: str | Path | None = None) -> dict[str, list[dict]]:
    """Load the chord-shape database (symbol -> list of voicing dicts)."""
    p = Path(path) if path else DEFAULT_SHAPES_PATH
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse(symbol: str) -> tuple[str, str]:
    """Parse a compact symbol into (root, quality).

    'C' -> ('C','maj'); 'Cm' -> ('C','min'); 'C7' -> ('C','7');
    'Cmaj7' -> ('C','maj7'); 'Cm7' -> ('C','min7').
    """
    s = symbol.strip()
    if s.endswith("maj7"):
        return s[:-4], "maj7"
    if s.endswith("m7"):
        return s[:-2], "min7"
    if s.endswith("7"):
        return s[:-1], "7"
    if s.endswith("m"):
        return s[:-1], "min"
    return s, "maj"


def _pc(root: str) -> int:
    return PITCH_CLASSES.index(root)


def _movable(root: str, quality: str, family: dict, n: int, fam_name: str) -> dict:
    rel_frets, fingers = family[quality]
    frets = [(-1 if f == -1 else f + n) for f in rel_frets]
    return {
        "frets": frets,
        "fingers": list(fingers),
        "base_fret": 1,
        "name": f"{root}{_SUFFIX[quality]} barre ({fam_name})",
    }


def _generate_movable(symbol: str) -> list[dict]:
    """Generate movable barre voicings for maj/min/7/maj7/min7 symbols.

    Returns both an E-shape and an A-shape barre (where the fret is >= 1), so
    voice-leading has options. Returns [] for unknown roots or qualities
    (e.g. diminished triads).
    """
    root, quality = _parse(symbol)
    if root not in PITCH_CLASSES or quality not in _E_SHAPE:
        return []
    r = _pc(root)
    out: list[dict] = []
    n_e = (r - 4) % 12  # E-shape fret (0 == open E)
    n_a = (r - 9) % 12  # A-shape fret (0 == open A)
    if n_e >= 1:
        out.append(_movable(root, quality, _E_SHAPE, n_e, "E-shape"))
    if n_a >= 1:
        out.append(_movable(root, quality, _A_SHAPE, n_a, "A-shape"))
    return out


def _voicing_position(v: dict) -> float:
    """Representative fret position = mean of the fingered (non-open) frets."""
    frets = [f for f in v["frets"] if f > 0]
    return sum(frets) / len(frets) if frets else 0.0


def _is_barre(v: dict) -> bool:
    """Heuristic: a barre if the lowest fingered fret appears on >= 2 strings."""
    active = [f for f in v["frets"] if f > 0]
    if not active:
        return False
    return active.count(min(active)) >= 2


def _pick_voicing(candidates: list[dict], prev_voicing: dict | None) -> dict:
    """Choose the voicing that best follows prev_voicing (voice-leading)."""
    def base_cost(c: dict) -> float:
        return _voicing_position(c) + (0.5 if _is_barre(c) else 0.0)

    if prev_voicing is None:
        return min(candidates, key=base_cost)
    prev_pos = _voicing_position(prev_voicing)
    return min(
        candidates,
        key=lambda c: abs(_voicing_position(c) - prev_pos) + 0.2 * base_cost(c),
    )


def _dedup(candidates: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for c in candidates:
        key = tuple(c["frets"])
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def attach_voicings(
    segments: list[dict], shapes: dict[str, list[dict]] | None = None
) -> list[dict]:
    """Attach guitar voicings to each segment with voice-leading.

    Candidates = known shapes plus generated movable barres. The candidate
    minimizing hand movement from the previous chord's chosen voicing is
    selected first (so renderers show it). "N" segments get an empty list.
    """
    if shapes is None:
        shapes = load_shapes()
    prev_voicing: dict | None = None
    for seg in segments:
        sym = (seg.get("symbol") or "N").strip()
        if sym == "N":
            seg["voicings"] = []
            seg["bass"] = seg.get("bass", seg.get("root"))
            prev_voicing = None
            continue
        candidates = _dedup(list(shapes.get(sym, [])) + _generate_movable(sym))
        if not candidates:
            seg["voicings"] = []
            seg["bass"] = seg.get("bass", seg.get("root"))
            prev_voicing = None
            continue
        chosen = _pick_voicing(candidates, prev_voicing)
        ordered = [chosen] + [c for c in candidates if c is not chosen]
        seg["voicings"] = ordered
        seg["bass"] = seg.get("bass", seg.get("root"))
        prev_voicing = chosen
    return segments
