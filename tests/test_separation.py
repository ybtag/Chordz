"""Tests for the optional Demucs separation (Stage 2b).

Skipped entirely if demucs/torch are not installed. These are lightweight
(import-level) checks only; the actual separation is exercised end-to-end via
the CLI on the Sweet Waltz sample.
"""
import pytest

pytest.importorskip("demucs")
pytest.importorskip("torch")

from chordz.separation import is_available, pick_device


def test_is_available_when_importable():
    assert is_available() is True


def test_pick_device_returns_valid():
    assert pick_device() in ("cuda", "xpu", "cpu")
