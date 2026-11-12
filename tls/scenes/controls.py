"""Settings > Controls: pick an action, press a new key. Conflicting keys swap. ESC cancels, 'Reset to defaults' restores everything."""
import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..constants import W, H, CYAN, AMBER, TEXT, DIM, GREEN, RED
from ..engine import Scene
from ..keymap import ACTIONS, LABEL
from .. import ui
from .menu import draw_backdrop


class ControlsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.sel = 0
        self.waiting = False
        self.msg, self.msg_ok = "", True
        self.t = 0.0

    def rows(self):
        return [a for a, *_ in ACTIONS] + ["reset", "back"]

    def update(self, dt):
        self.t += dt

    def key_press(self, k):
        km = self.game.keymap
        K = Qt.Key
        rows = self.rows()
        if self.waiting:
            if k == K.Key_Escape:
                self.waiting, self.msg = False, ""
                return
            ok, msg = km.rebind(rows[self.sel], k)
            self.msg, self.msg_ok = (msg or ("Bound." if ok else "")), ok
            if not ok:
                self.game.audio.play("bad", .5)
                return
            self.waiting = False
            self.game.audio.play("ok", .5)
            self.game.save.save()
            return
        if k == K.Key_Escape:
            self.game.save.save()
            self.game.pop()
        elif k in (K.Key_W, K.Key_Up):
            self.sel = (self.sel - 1) % len(rows)
        elif k in (K.Key_S, K.Key_Down):
            self.sel = (self.sel + 1) % len(rows)
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space):
            r = rows[self.sel]
            if r == "back":
                self.game.save.save()
                self.game.pop()
            elif r == "reset":
                km.reset()
                self.msg, self.msg_ok = "Controls reset to defaults.", True
                self.game.save.save()
            else:
                self.waiting, self.msg = True, ""

    def draw(self, p):
        km = self.game.keymap
        draw_backdrop(p, self.t)
        p.fillRect(0, 0, W, H, QColor(2, 4, 10, 205))
        ui.text_spaced(p, "CONTROLS", W / 2, 24, CYAN, 13, 3, True, True)
        for i, r in enumerate(self.rows()):
            on = i == self.sel
            y = 40 + i * 13
            if r in LABEL:
                label = LABEL[r]
                key = "press a key..." if (on and self.waiting) else km.name(r)
                alt = " / arrows" if r in ("up", "down", "left", "right") else ""
                ui.text(p, ("> " if on else "  ") + label, 120, y + 9, AMBER if on else TEXT, 8, on)
                ui.text(p, key + ("" if (on and self.waiting) else alt), 300, y + 9, GREEN if not (on and self.waiting) else AMBER, 8, True)
            else:
                ui.text(p, ("> " if on else "  ") + ("Reset to defaults" if r == "reset" else "Back"), 120, y + 9, AMBER if on else TEXT, 8, on)
        if self.msg:
            ui.text(p, self.msg, W / 2, 238, GREEN if self.msg_ok else RED, 8, True, True)
        ui.text(p, "W/S choose   ENTER rebind   ESC back", W / 2, H - 6, DIM, 7, False, True)
