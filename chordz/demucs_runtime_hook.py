"""Use the htdemucs model bundled with the Chordz heavy executable."""
import ctypes
import os
from pathlib import Path
import sys


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _bundle_root = Path(sys._MEIPASS)
    _torch_lib = _bundle_root / "torch" / "lib"
    if os.name == "nt":
        _torch_dll_directory = os.add_dll_directory(str(_torch_lib))
        _preloaded_c10 = ctypes.CDLL(str(_torch_lib / "c10.dll"))

    import demucs.api as _demucs_api

    _bundled_repo = _bundle_root / "demucs_models"
    _original_get_model = _demucs_api.get_model

    def _get_bundled_model(name: str, repo=None):
        return _original_get_model(name=name, repo=repo or _bundled_repo)

    _demucs_api.get_model = _get_bundled_model
