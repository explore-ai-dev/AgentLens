"""Pure Windows console input compatibility helpers."""

from __future__ import annotations


def should_drop_key_event(control_state: int, virtual_key: int, unicode_char: str) -> bool:
    """Drop non-character control records but preserve committed IME text."""
    return bool(control_state and virtual_key == 0 and not unicode_char)
