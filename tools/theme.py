"""Shared visual language for every generated asset.

Warm terminal palette: near-black charcoal, cream text, amber accent, a
restrained green for prompts and a red/orange only in the window chrome.
"""

BG = "#0d0d0f"
CHROME = "#161619"
BORDER = "#2a2a30"
TEXT = "#e9e1d1"          # warm off-white
MUTED = "#8b8578"         # warm grey
DIM = "#3a3a41"

AMBER = "#e8a33d"
AMBER_SOFT = "#f0bd6e"
GREEN = "#8ec07c"
RED = "#d65d3e"

# card surfaces
CARD_TOP = "#1c1c21"
CARD_BOTTOM = "#141417"
LIFT_NEAR = "#45454f"     # closest shadow layer
LIFT_FAR = "#2f2f36"      # deepest shadow layer

MONO = "ui-monospace,'JetBrains Mono','SFMono-Regular',Menlo,Consolas,'DejaVu Sans Mono',monospace"

# level 0-9 of the ASCII ramp -> colour. Warm greys rising to cream so the
# portrait sits in the same light as the rest of the terminal.
PORTRAIT_RAMP = {
    2: "#35332e",
    3: "#4b4841",
    4: "#666257",
    5: "#807b6e",
    6: "#9a9486",
    7: "#b8b1a1",
    8: "#d5cdb9",
    9: "#f4eee1",
}


def esc(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
