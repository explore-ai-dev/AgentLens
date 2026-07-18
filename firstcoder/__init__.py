"""FirstCoder package."""

from __future__ import annotations

import os


# Textual reads this before selecting its platform driver. Keep the override
# opt-in to Windows so other terminal backends are unaffected.
if os.name == "nt":
    os.environ.setdefault("TEXTUAL_DRIVER", "firstcoder.textual_windows_driver:WindowsDriver")
