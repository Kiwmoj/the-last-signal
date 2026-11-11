"""Typewriter dialogue boxes with a distinct look per kind of message.

styles:
  plain    - narration / examination
  radio    - old radio transmissions (live waveform, tinted by frequency)
  terminal - computer messages (green phosphor)
  note     - research notes and written pages (paper tones)
  voice    - mysterious recordings (violet, glitching characters)
"""
import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from .constants import CYAN, AMBER, TEXT
from .world import TINT, FREQS
from . import ui

SPEED = 70.0     # characters per second

LOOK = {
    "plain": dict(border=CYAN, head=AMBER, body=TEXT, tag=""),
    "radio": dict(border=None, head=None, body=QColor(200, 235, 245), tag="TRANSMISSION"),
    "terminal": dict(border=QColor(90, 255, 150), head=QColor(90, 255, 150), body=QColor(150, 255, 190), tag="STATION TERMINAL"),
    "note": dict(border=QColor(200, 150, 80), head=QColor(235, 190, 110), body=QColor(235, 220, 190), tag="HANDWRITTEN"),
    "voice": dict(border=QColor(190, 90, 255), head=QColor(220, 140, 255), body=QColor(225, 190, 255), tag="UNKNOWN RECORDING"),
}


class Dialog:
    def __init__(self, who, lines, style="plain", freq=0, on_done=None):
        """`lines` are strings, or (speaker, text[, style]) tuples for conversations with several speakers."""
        texts, meta = [], []
        for ln in (list(lines) or [""]):
            if isinstance(ln, str):
                texts.append(ln)
                meta.append((who, style))
            else:
                texts.append(ln[1])
                meta.append((ln[0], ln[2] if len(ln) > 2 else style))
        self.lines, self.meta = texts, meta
        self.freq = freq
        self.on_done = on_done          # called once when the player closes the last page
        self.i = 0
        self.shown = 0.0
        self.age = 0.0
        self._last = 0

    @property
    def who(self):
        return self.meta[self.i][0]

    @property
    def style(self):
        s = self.meta[self.i][1]
        return s if s in LOOK else "plain"

    @property
    def full(self):
        return self.lines[self.i]

    @property
    def done_typing(self):
        return self.shown >= len(self.full)

    def update(self, dt):
        """Advance the typewriter. Returns True when a new visible character was typed (for the blip)."""
        self.shown = min(len(self.full), self.shown + dt * SPEED)
        self.age += dt
        n = int(self.shown)
        typed = n > self._last and n % 3 == 0 and n <= len(self.full) and self.full[n - 1:n] != " "
        self._last = n
        return typed

    def advance(self):
        """Skip the typewriter, then page forward. Returns True when the dialogue is finished."""
        if not self.done_typing:
            self.shown = len(self.full)
            return False
        if self.i + 1 < len(self.lines):
            self.i += 1
            self.shown = 0.0
            self._last = 0
            return False
        return True

    def draw(self, p, t):
        look = LOOK[self.style]
        tint = QColor(*TINT[self.freq])
        border = look["border"] or tint
        head = look["head"] or tint
        x, y, w, h = 16, 184, 448, 74
        # entrance: the box slides up and fades in
        a = min(1.0, self.age * 6)
        p.save()
        p.setOpacity(a)
        p.translate(0, (1 - a) * 8)
        if self.style == "note":
            p.fillRect(x, y, w, h, QColor(34, 26, 18, 238))
        elif self.style == "terminal":
            p.fillRect(x, y, w, h, QColor(3, 16, 8, 240))
        elif self.style == "voice":
            p.fillRect(x, y, w, h, QColor(18, 4, 30, 240))
        else:
            ui.panel(p, x, y, w, h, border)
        if self.style != "plain" and self.style != "radio":
            p.setPen(border)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(x, y, w - 1, h - 1)
        if self.style == "terminal":
            p.setPen(QColor(90, 255, 150, 22))
            for sy in range(y + 2, y + h, 3):
                p.drawLine(x + 1, sy, x + w - 2, sy)
        tag = look["tag"]
        if self.style == "radio":
            tag = f"TRANSMISSION  {FREQS[self.freq]} MHz"
            ui.scope(p, x + w - 96, y + 6, 88, 18, t, tint, .8, .15)
            p.setOpacity(a)
        elif self.style == "voice":
            ui.scope(p, x + w - 96, y + 6, 88, 18, t, QColor(220, 140, 255), 1.0, .5)
            p.setOpacity(a)
        ui.text(p, self.who, x + 12, y + 16, head, 8, True, glow=True)
        if tag:
            ui.text(p, tag, x + 12, y + 28 if self.style == "plain" else y + 27, QColor(head.red(), head.green(), head.blue(), 140), 6)
        ui.type_lines(p, self.full, self.shown, x + 12, y + 41, w - 24, look["body"], 8, 11,
                      glitch=.07 if self.style == "voice" else 0.0, t=t)
        if self.done_typing and int(t * 2) % 2 == 0:
            more = self.i + 1 < len(self.lines)
            ui.text(p, "[E] " + ("next" if more else "close"), x + w - 62, y + h - 5, border, 7)
        p.restore()
