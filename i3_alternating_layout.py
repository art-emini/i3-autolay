#!/usr/bin/env python3
"""
i3-alternating-layout
─────────────────────
Alternates splith → splitv as windows open/close.
Direction derived from real window count — nothing to drift.

  1 window  → arm splith  (2nd opens side by side)
  2 windows → arm splitv  (3rd opens below)
  3 windows → arm splith
  ...

Requirements:  pip install i3ipc --break-system-packages
Install:       cp i3_alternating_layout.py ~/.config/scripts/
               chmod +x ~/.config/scripts/i3_alternating_layout.py
i3 config:     exec --no-startup-id ~/.config/scripts/i3_alternating_layout.py
Reload:        pkill -f i3_alternating_layout.py && python3 ~/.config/scripts/i3_alternating_layout.py &
"""

import i3ipc
import logging
import sys

log = logging.getLogger("alt-layout")
logging.basicConfig(level=logging.INFO, format="[alt-layout] %(message)s", stream=sys.stdout)

# ── State ──────────────────────────────────────────────────────────────────────

window_to_ws: dict[int, str] = {}   # win_id → workspace name  (O(1) close lookup)
ws_counts:    dict[str, int] = {}   # workspace name → count    (O(1) focus lookup)
_last_armed:  dict[str, str] = {}   # workspace name → last direction (dedup IPC calls)

# ── Core ───────────────────────────────────────────────────────────────────────

def _direction(count: int) -> str:
    return "splith" if count % 2 == 1 else "splitv"


def _arm(i3: i3ipc.Connection, ws: str, count: int) -> None:
    d = _direction(count)
    if _last_armed.get(ws) == d:
        return
    _last_armed[ws] = d
    i3.command(d)
    log.info(f"[{ws}] {count} win → {d}")


def _resync(i3: i3ipc.Connection, ws_name: str) -> int:
    """Full resync for one workspace from the live tree. Only called on close."""
    for ws in i3.get_tree().workspaces():
        if ws.name != ws_name:
            continue
        leaves = [n for n in ws.leaves() if n.type == "con"]
        # Rebuild reverse map for this workspace
        for win_id, name in list(window_to_ws.items()):
            if name == ws_name:
                del window_to_ws[win_id]
        for n in leaves:
            window_to_ws[n.id] = ws_name
        count = len(leaves)
        ws_counts[ws_name] = count
        return count
    ws_counts[ws_name] = 0
    return 0

# ── Events ─────────────────────────────────────────────────────────────────────

def on_window_new(i3: i3ipc.Connection, e) -> None:
    con = e.container
    if con.floating in ("user_on", "auto_on"):
        return

    ws_node = con.workspace()
    if not ws_node:
        focused = i3.get_tree().find_focused()
        if not focused:
            return
        ws_node = focused.workspace()

    ws = ws_node.name
    window_to_ws[con.id] = ws
    count = ws_counts.get(ws, 0) + 1
    ws_counts[ws] = count
    _arm(i3, ws, count)


def on_window_close(i3: i3ipc.Connection, e) -> None:
    con = e.container
    ws = window_to_ws.pop(con.id, None)
    if ws is None:
        return
    count = _resync(i3, ws)  # resync on close — only tree walk in hot path
    _arm(i3, ws, count)


def on_window_focus(i3: i3ipc.Connection, e) -> None:
    con = e.container
    if con.floating in ("user_on", "auto_on"):
        return
    ws = window_to_ws.get(con.id)
    if ws:
        _arm(i3, ws, ws_counts.get(ws, 0))  # O(1) — no tree walk


def on_workspace_focus(i3: i3ipc.Connection, e) -> None:
    ws = e.current
    if ws:
        _arm(i3, ws.name, ws_counts.get(ws.name, 0))  # O(1) — no tree walk

# ── Startup ────────────────────────────────────────────────────────────────────

def sync_from_tree(i3: i3ipc.Connection) -> None:
    """One-time full tree walk at startup only."""
    for ws in i3.get_tree().workspaces():
        leaves = [n for n in ws.leaves() if n.type == "con"]
        for n in leaves:
            window_to_ws[n.id] = ws.name
        ws_counts[ws.name] = len(leaves)
        log.info(f"[{ws.name}] synced {len(leaves)} window(s)")
        _arm(i3, ws.name, len(leaves))


def main() -> None:
    try:
        i3 = i3ipc.Connection()
    except Exception as e:
        log.error(f"Could not connect to i3 IPC: {e}")
        sys.exit(1)

    log.info("started")
    sync_from_tree(i3)

    i3.on(i3ipc.Event.WINDOW_NEW,      on_window_new)
    i3.on(i3ipc.Event.WINDOW_CLOSE,    on_window_close)
    i3.on(i3ipc.Event.WINDOW_FOCUS,    on_window_focus)
    i3.on(i3ipc.Event.WORKSPACE_FOCUS, on_workspace_focus)

    try:
        i3.main()
    except KeyboardInterrupt:
        log.info("stopped.")
    except Exception as e:
        log.error(f"fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
