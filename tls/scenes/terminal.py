"""Station terminal: a file browser whose contents depend on the tuned frequency.

Files can be locked until a puzzle is solved (PERSONAL.LOG needs the Old Radio message).
Reading a file adds its clue to the journal.
"""
import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..constants import W, H, DIM, RED
from ..story import TERMINAL
from ..world import FREQS, FREQ_NAMES, TINT
from .. import ui
from .overlay import Overlay, Typer, elide

GREEN = QColor(90, 255, 150)
GREEN_DIM = QColor(50, 150, 90)
PHOSPHOR = QColor(150, 255, 190)


class TerminalScene(Overlay):
    """File browser. `data` maps band -> files (defaults to the station terminal); a file whose lock starts with '+'
    only appears once that flag is set (new messages show up as the story advances)."""

    def __init__(self, game, gp, data=None, title="STATION 09  //  STATION TERMINAL"):
        super().__init__(game, gp)
        self.data, self.title = data or TERMINAL, title
        self.sel = 0
        self.reader = None       # (title, Typer, denied)
        self.last_freq = gp.freq
        self.glitch = 0.0
        self.audio.play("click")

    def files(self):
        flags = self.gp.flags
        return [f for f in self.data[self.gp.freq] if not (f[1] and f[1].startswith("+") and f[1][1:] not in flags)]

    def is_locked(self, lock):
        return bool(lock and not lock.startswith("+") and lock not in self.gp.flags)

    def tick(self, dt):
        if self.gp.freq != self.last_freq:          # tuned to another band: the file system changes
            self.last_freq = self.gp.freq
            self.sel, self.reader, self.glitch = 0, None, .5
        self.glitch = max(0.0, self.glitch - dt)
        if self.reader and self.reader[1].update(dt):
            self.audio.play("blip", .35)

    def key_press(self, k):
        K = Qt.Key
        n = len(self.files())
        if k == K.Key_Escape:
            self.audio.play("click")
            self.close()
        elif self.tune_key(k):
            pass
        elif k in (K.Key_W, K.Key_Up):
            self.sel = (self.sel - 1) % n
            self.audio.play("click", .4)
        elif k in (K.Key_S, K.Key_Down):
            self.sel = (self.sel + 1) % n
            self.audio.play("click", .4)
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E):
            self.open_file(self.sel)

    def open_file(self, i):
        name, lock, text, clue = self.files()[i]
        if self.is_locked(lock):
            self.reader = (name, Typer("ACCESS DENIED. This file is encrypted. The terminal cannot decrypt it on its own. "
                                       "A restored transmission might hold the key.", 70), True)
            self.audio.play("bad")
            return
        self.reader = (name, Typer(text, 90), False)
        self.gp.read.add("file:" + name)
        self.gp.learn(clue)
        self.audio.play("click")

    # ------------------------------------------------------------------ drawing
    def draw(self, p):
        gp, t = self.gp, self.t
        f = gp.freq
        tint = QColor(*TINT[f])
        p.save()
        ui.overlay_open(p, t, 190)
        x, y, w, h = 26, 20, 428, 230
        p.fillRect(x, y, w, h, QColor(2, 12, 6, 248))
        p.setPen(GREEN)
        p.drawRect(x, y, w - 1, h - 1)
        p.fillRect(x + 1, y + 1, w - 2, 16, QColor(tint.red() // 5, tint.green() // 5, tint.blue() // 5))
        ui.text(p, self.title, x + 8, y + 13, GREEN, 8, True, glow=True)
        ui.text(p, f"{FREQS[f]} MHz  {FREQ_NAMES[f]}", x + w - 8 - 150, y + 13, tint, 8, True)

        if t < .7:                                       # boot sequence
            for i, ln in enumerate(["BOOT  STN09-OS 1.1", "CHECKING MEMORY ........ OK", "MOUNTING /STATION ....... OK",
                                    "LISTENING ON BAND " + f"{FREQS[f]}"]):
                if t > i * .16:
                    ui.text(p, ln, x + 12, y + 36 + i * 12, GREEN_DIM, 8)
            p.restore()
            return

        # file list
        ui.text(p, "FILES", x + 12, y + 32, GREEN_DIM, 7, True)
        p.fillRect(x + 8, y + 36, 150, 1, GREEN_DIM)
        for i, (name, lock, _, _) in enumerate(self.files()):
            yy = y + 52 + i * 16
            locked = self.is_locked(lock)
            on = i == self.sel
            if on:
                p.fillRect(x + 8, yy - 11, 150, 14, QColor(40, 120, 70, 110 + int(40 * math.sin(t * 6))))
            mark = "[#]" if locked else ("   " if ("file:" + name) in gp.read else " * ")
            col = RED if locked else (GREEN if on else PHOSPHOR)
            ui.text(p, mark + name, x + 12, yy, col, 7)
        ui.text(p, "Files change with the frequency.", x + 10, y + h - 40, GREEN_DIM, 6)
        ui.text(p, "Tune with [Q] / [SPACE].", x + 10, y + h - 31, GREEN_DIM, 6)

        # reading pane
        p.fillRect(x + 166, y + 24, 1, h - 48, GREEN_DIM)
        if self.reader:
            title, ty, denied = self.reader
            ui.text(p, title, x + 176, y + 32, RED if denied else GREEN, 8, True, glow=True)
            ui.type_lines(p, ty.text, ty.shown, x + 176, y + 50, w - 192, RED if denied else PHOSPHOR, 8, 12,
                          glitch=.06 if f == 2 else 0.0, t=t)
            if ty.done and int(t * 2) % 2 == 0:
                ui.text(p, "_", x + 176, y + h - 30, GREEN, 8)
        else:
            ui.text(p, "Select a file and press ENTER.", x + 176, y + 40, GREEN_DIM, 8)
            if int(t * 2) % 2 == 0:
                ui.text(p, "_", x + 176, y + 54, GREEN, 8)
        ui.text(p, "W/S select   ENTER open   Q tune   SPACE radio   ESC log off", x + 8, y + h - 8, GREEN_DIM, 7)
        # CRT scanlines + the band-change glitch
        p.setPen(QColor(90, 255, 150, 16))
        for sy in range(y + 18, y + h - 1, 3):
            p.drawLine(x + 1, sy, x + w - 2, sy)
        if self.glitch > 0:
            p.fillRect(x + 1, y + int(self.glitch * 300) % h, w - 2, 5, QColor(tint.red(), tint.green(), tint.blue(), 90))
        p.restore()
