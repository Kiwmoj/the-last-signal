"""Gamepad support through Windows XInput (Xbox-compatible controllers), using only ctypes. If XInput or a controller is missing the
game simply plays with the keyboard.

The pad produces ordinary key events, so every screen works with it:
  left stick / D-pad  move + menu navigation        A  interact / confirm        B, Start  back / pause
  X  radio on-off     LB  change frequency          RB  Echo Receiver           Y  journal      Back  hint
"""
import ctypes
import sys
from PyQt6.QtCore import Qt

K = Qt.Key
DEAD = 8000
BTN = {"up": 0x0001, "down": 0x0002, "left": 0x0004, "right": 0x0008, "start": 0x0010, "back": 0x0020,
       "lb": 0x0100, "rb": 0x0200, "a": 0x1000, "b": 0x2000, "x": 0x4000, "y": 0x8000}


class _Pad(ctypes.Structure):
    _fields_ = [("buttons", ctypes.c_ushort), ("lt", ctypes.c_ubyte), ("rt", ctypes.c_ubyte),
                ("lx", ctypes.c_short), ("ly", ctypes.c_short), ("rx", ctypes.c_short), ("ry", ctypes.c_short)]


class _State(ctypes.Structure):
    _fields_ = [("packet", ctypes.c_ulong), ("pad", _Pad)]


def _load():
    if sys.platform != "win32":
        return None
    for name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            return ctypes.WinDLL(name).XInputGetState
        except (OSError, AttributeError):
            continue
    return None


class Gamepad:
    def __init__(self, game):
        self.game = game
        self.get = _load()
        self.connected = False
        self.retry = 0.0
        self.prev = 0                     # buttons incl. virtual stick directions, as a bit mask
        self.held = set()                 # movement keys currently held by the pad

    def state(self):
        """(buttons, lx, ly) of controller 0 or None. Separate so tests can replace it."""
        if self.get is None:
            return None
        st = _State()
        if self.get(0, ctypes.byref(st)) != 0:
            return None
        p = st.pad
        return p.buttons, p.lx, p.ly

    def poll(self, dt):
        if self.get is None:
            return
        if not self.connected:
            self.retry -= dt              # looking for a controller is slow, so only try every 1.5 s
            if self.retry > 0:
                return
            self.retry = 1.5
        s = self.state()
        self.connected = s is not None
        if s is None:
            self._release_all()
            return
        buttons, lx, ly = s
        mask = buttons
        if lx < -DEAD: mask |= BTN["left"]
        if lx > DEAD: mask |= BTN["right"]
        if ly > DEAD: mask |= BTN["up"]
        if ly < -DEAD: mask |= BTN["down"]
        self._apply(mask)

    # ---- turning the pad into key events ----
    def _apply(self, mask):
        g = self.game
        new = mask & ~self.prev
        for name, key in (("up", K.Key_Up), ("down", K.Key_Down), ("left", K.Key_Left), ("right", K.Key_Right)):
            down = bool(mask & BTN[name])
            if down and key not in self.held:
                self.held.add(key)
                g.key_down(key)                           # menus see a press; the world sees a held key
            elif not down and key in self.held:
                self.held.discard(key)
                g.key_up(key)
        km = g.keymap
        in_world = hasattr(g.scenes[-1], "dialog")
        taps = {"a": km.primary("interact") if in_world else K.Key_Return, "b": K.Key_Escape, "start": K.Key_Escape,
                "x": km.primary("radio"), "lb": km.primary("tune"), "rb": km.primary("echo"), "y": km.primary("journal"),
                "back": km.primary("hint")}
        for name, key in taps.items():
            if new & BTN[name]:
                g.key_down(key)
                g.key_up(key)
        self.prev = mask

    def _release_all(self):
        for key in list(self.held):
            self.game.key_up(key)
        self.held.clear()
        self.prev = 0
