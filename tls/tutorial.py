"""Gradual, contextual tutorial. One hint at a time, each shown only when it becomes relevant and
removed the moment the player does the thing. Progress is stored in gp.flags so it is saved."""
import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from .constants import AMBER, TEXT, DIM, CYAN
from . import ui

# (id, key caps, text, should-show(gp, flags), done flag)
STEPS = [
    ("move", ["W", "A", "S", "D"], "Move around  (arrow keys work too)",
     lambda gp, f: gp.t > 1.5, "tut_move"),
    ("interact", ["E"], "Interact with what you are standing next to",
     lambda gp, f: "tut_move" in f and gp.focus is not None, "tut_interact"),
    ("radio", ["SPACE"], "Switch your radio on",
     lambda gp, f: "echo_found" in f, "radio_used"),
    ("tune", ["Q"], "Change frequency",
     lambda gp, f: "radio_used" in f and gp.radio_on, "tuned"),
    ("echo", ["R"], "Open the Echo Receiver",
     lambda gp, f: "tuned" in f and "echo_found" in f, "echo_opened"),
    ("journal", ["J"], "Open your journal to review clues",
     lambda gp, f: "src_tut" in f, "journal_opened"),
    ("pause", ["ESC"], "Pause the game or save",
     lambda gp, f: "journal_opened" in f, "pause_opened"),
]


class Tutorial:
    def __init__(self):
        self.cur = None
        self.a = 0.0
        self.age = 0.0

    def current(self, gp):
        if gp.dialog or gp.frozen or gp.fade > .3 or gp.events or gp.current_event:
            return None
        f = gp.flags
        for sid, keys, text, show, done in STEPS:
            if done not in f and show(gp, f):
                return sid
        return None

    def update(self, gp, dt):
        want = self.current(gp)
        if want != self.cur:                      # fade the old hint out, then swap in the new one
            self.a = max(0.0, self.a - dt * 5)
            if self.a <= 0.02:
                self.cur, self.age = want, 0.0
            return
        if self.cur is None:
            return
        self.age += dt
        self.a = min(1.0, self.a + dt * 3)
        if self.cur == "pause" and self.age > 9:      # informational: do not nag forever
            gp.flags.add("pause_opened")

    def draw(self, p, gp):
        if self.cur is None or self.a <= 0.02:
            return
        step = next(s for s in STEPS if s[0] == self.cur)
        _, keys, text, _, _ = step
        a = self.a
        slide = (1 - a) * -14
        p.save()
        p.setOpacity(a)
        p.translate(slide, 0)
        x, y = 6, 58
        pulse = .5 + .5 * math.sin(gp.t * 5)
        kw = [max(12, 6 * len(k) + 8) for k in keys]
        w = sum(kw) + 4 * len(keys) + 12 + len(text) * 5 + 6
        ui.panel(p, x, y, w, 24, QColor(255, 200, 90, 160))
        cx = x + 6
        for k, wd in zip(keys, kw):
            p.fillRect(cx, y + 4, wd, 15, QColor(50, 56, 70))
            p.fillRect(cx, y + 4, wd, 1, QColor(140, 150, 175))
            p.fillRect(cx, y + 17, wd, 2, QColor(18, 22, 30))
            p.fillRect(cx, y + 4, wd, 15, QColor(255, 200, 90, int(30 * pulse)))
            ui.text(p, k, cx + wd / 2, y + 15, AMBER, 7, True, True)
            cx += wd + 4
        ui.text(p, text, cx + 4, y + 15, TEXT, 7)
        p.restore()
