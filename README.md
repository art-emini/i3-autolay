# i3-autolay

> Automatic alternating window layout for i3wm — zero config, zero drift.

![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![i3wm](https://img.shields.io/badge/i3wm-compatible-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)

---

## What it does

Every time you open a window, i3-autolay automatically switches the split direction so your layout always makes sense — no keybinds, no manual splits, no thinking about it.

```
1 window   →  open 2nd  →  side by side     (splith)
2 windows  →  open 3rd  →  stacked below    (splitv)
3 windows  →  open 4th  →  side by side     (splith)
...
```

Close windows and open new ones — it resyncs from the real i3 tree and stays correct no matter what.

---

## Features

- **Automatic alternating splits** — `splith → splitv → splith` on every new window
- **Close-aware** — resyncs from the live i3 tree on close so counts never drift
- **Workspace-aware** — each workspace tracks its own split state independently; switching workspaces re-arms the correct direction instantly
- **Float-aware** — floating windows are completely ignored, only tiling windows affect the layout
- **Zero config** — works out of the box with sensible defaults
- **IPC dedup** — skips redundant `i3.command()` calls if the direction hasn't changed, keeping IPC traffic minimal
- **Startup sync** — if you restart the script with windows already open, it reads the live tree and seeds state correctly
- **Lightweight** — two small dicts and an event loop; ~15MB Python baseline, zero CPU at idle

---

## Requirements

- Python 3.10+
- i3wm
- [i3ipc](https://github.com/altdesktop/i3ipc-python)

```bash
pip install i3ipc --break-system-packages
```

---

## Install

```bash
# Clone
git clone https://github.com/yourusername/i3-autolay.git
cd i3-autolay

# Install dependency
pip install i3ipc --break-system-packages

# Place the script
mkdir -p ~/.config/scripts
cp i3_alternating_layout.py ~/.config/scripts/
chmod +x ~/.config/scripts/i3_alternating_layout.py
```

---

## Autostart with i3

Add this line to your `~/.config/i3/config`:

```
exec --no-startup-id ~/.config/scripts/i3_alternating_layout.py
```

Then reload i3:

```
$mod + Shift + R
```

---

## Run manually

```bash
# Run in background
python3 ~/.config/scripts/i3_alternating_layout.py &

# Restart after an update
pkill -f i3_alternating_layout.py && python3 ~/.config/scripts/i3_alternating_layout.py &

# Check it's running
pgrep -a python3
```

---

## How it works

i3-autolay connects to i3's IPC socket via `i3ipc` and listens for four events:

| Event | Action |
|---|---|
| `WINDOW_NEW` | Increments workspace count, arms next split direction |
| `WINDOW_CLOSE` | Resyncs count from live tree, re-arms correct direction |
| `WINDOW_FOCUS` | Re-arms split for the focused window's workspace (O(1), no tree walk) |
| `WORKSPACE_FOCUS` | Re-arms split when switching workspaces (O(1), no tree walk) |

The split direction is derived purely from the window count — there's no separate index to get out of sync. `count % 2 == 1` → `splith`, `count % 2 == 0` → `splitv`. Simple, correct, always.

Tree walks only happen at startup (once) and on window close (scoped to the affected workspace). Every other event is O(1).

---

## Customization

Want to start with `splitv` instead? Swap the logic in `_direction()`:

```python
def _direction(count: int) -> str:
    return "splitv" if count % 2 == 1 else "splith"
```

---

## License

MIT
