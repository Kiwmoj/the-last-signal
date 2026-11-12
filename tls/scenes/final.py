"""Chapter 5: the Final Transmitter puzzle and the last decision.

FinalScene   - feed the transmitter one band at a time; each correct tone in Elias's order locks one line of the
               final transmission. The assembled message is the one that began the player's night.
DecisionScene - send the warning (rewrite history) or shut the transmitter down. Each leads to its own ending.
"""
import math
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPen

from ..constants import W, H, CYAN, AMBER, TEXT, DIM, GREEN, RED
from ..story import FINAL_ORDER, FINAL_LINES, REWARD, DECISION, DECISION_INTRO
from ..world import FREQS, FREQ_NAMES, TINT
from .. import ui
from .overlay import Overlay, Typer
from .puzzles import _frame


class FinalScene(Overlay):
    def __init__(self, game, gp):
        super().__init__(game, gp)
        self.seq = []
        self.lines = []                  # (band, Typer) already locked in
        self.msg, self.msg_col, self.msg_t = "", TEXT, 0.0
        self.flash = 0.0
        self.done = "final_ready" in gp.flags
        if self.done:
            self.lines = [(b, Typer(FINAL_LINES[b], 200)) for b in FINAL_ORDER]
            for _, ty in self.lines:
                ty.finish()
        self.audio.play("click")

    def tick(self, dt):
        self.msg_t = max(0.0, self.msg_t - dt)
        self.flash = max(0.0, self.flash - dt * 2)
        for _, ty in self.lines:
            if ty.update(dt):
                self.audio.play("blip", .35)

    def key_press(self, k):
        K, gp = Qt.Key, self.gp
        if k == K.Key_Escape:
            self.close()
        elif self.tune_key(k):
            pass
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E):
            if self.done:
                self.close()
                from .final import DecisionScene
                self.game.push(DecisionScene(self.game, gp))
            else:
                self.send(gp.eff)
        elif k == K.Key_Backspace and not self.done:
            self.seq, self.lines = [], []

    def send(self, band):
        gp = self.gp
        want = FINAL_ORDER[len(self.seq)]
        if band == want:
            self.seq.append(band)
            ty = Typer(FINAL_LINES[band], 40)
            self.lines.append((band, ty))
            self.flash = .6
            self.audio.play("ok", .6)
            if len(self.seq) == 3:
                self.done = True
                gp.complete("final_ready", "The Final Transmission", REWARD["final_ready"])
                gp.record("final_msg", 2, "The final transmission", "Station 09... if anyone can hear this... do not open the archive... it knows you're listening.")
                self.msg, self.msg_col, self.msg_t = "TRANSMISSION ASSEMBLED", GREEN, 6
        else:
            self.seq, self.lines = [], []
            self.flash = 1.0
            self.msg, self.msg_col, self.msg_t = "WRONG TONE. The message falls apart. Start again.", RED, 3.0
            self.audio.play("bad")

    def draw(self, p):
        gp, t = self.gp, self.t
        f = gp.eff
        tint = QColor(*TINT[f])
        p.save()
        ui.overlay_open(p, t, 185)
        x, y, w, h = 22, 14, 436, 242
        _frame(p, x, y, w, h, "FINAL TRANSMITTER  //  STATION 09", GREEN if self.done else tint, "READY" if self.done else "ASSEMBLING")
        if not self.done:
            ui.type_lines(p, "The transmitter carries one message, and it needs it in three parts: each band locks one line. "
                             "Elias's notes on the lectern give the order. Tune a band (Q), then send its tone with ENTER.",
                          99999, x + 12, y + 32, w - 24, TEXT, 7, 9)
            n = sum(1 for k in ("final_1", "final_2", "final_3") if gp.journal.has(k))
            ui.text(p, f"ELIAS'S NOTES FOUND: {n}/3", x + 12, y + 68, AMBER if n < 3 else GREEN, 7, True)
        ui.scope(p, x + 12, y + 76, 250, 56, t, tint, 1.0, .05 if gp.radio_on else .5)
        ui.text(p, f"BAND {FREQS[f]} MHz  {FREQ_NAMES[f]}", x + 12, y + 146, tint, 8, True)
        for i in range(3):
            c = QColor(*TINT[FINAL_ORDER[i]]) if i < len(self.seq) or self.done else QColor(60, 70, 90)
            bx = x + 280 + i * 50
            p.fillRect(bx, y + 78, 42, 24, QColor(10, 16, 26))
            p.setPen(c)
            p.drawRect(bx, y + 78, 41, 23)
            ui.text(p, str(i + 1), bx + 17, y + 94, c, 9, True)
        ui.text(p, "THE MESSAGE", x + 12, y + 166, DIM, 7, True)
        for i, (band, ty) in enumerate(self.lines):
            ui.text(p, ty.text[:int(ty.shown)], x + 14, y + 180 + i * 13, QColor(*TINT[band]), 9, True)
        if self.done:
            ui.text(p, "[ENTER] decide what to send" if int(t * 2) % 2 == 0 else "", x + w - 190, y + h - 8, GREEN, 8, True)
        else:
            ui.text(p, f"[ENTER] send {FREQS[f]} MHz as tone {len(self.seq) + 1}", x + 12, y + 222, AMBER, 7, True)
            ui.text(p, "Q tune  SPACE radio  ENTER send  BKSP restart  ESC leave", x + 12, y + h - 7, DIM, 7)
        if self.msg_t > 0:
            ui.text(p, self.msg, x + w / 2, y + 206, QColor(self.msg_col.red(), self.msg_col.green(), self.msg_col.blue(),
                                                            int(255 * min(1, self.msg_t))), 8, True, True, True)
        if self.flash > 0:
            c = GREEN if self.msg_col == GREEN or not self.msg_t else RED
            p.fillRect(x, y, w, h, QColor(c.red(), c.green(), c.blue(), int(50 * self.flash)))
        p.restore()


class DecisionScene(Overlay):
    live = False

    def __init__(self, game, gp):
        super().__init__(game, gp)
        self.sel = 0
        self.keys = ("warn", "silence")                  # the last decision is always a choice between two
        self.rects = [QRectF(30, 118, 200, 112), QRectF(250, 118, 200, 112)]
        self.audio.play("rise", .6)

    def key_press(self, k):
        K = Qt.Key
        if k == K.Key_Escape:
            self.close()
        elif k in (K.Key_A, K.Key_Left):
            self.sel = (self.sel - 1) % len(self.keys)
            self.audio.play("click", .4)
        elif k in (K.Key_D, K.Key_Right):
            self.sel = (self.sel + 1) % len(self.keys)
            self.audio.play("click", .4)
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space):
            self.choose(self.sel)

    def mouse_move(self, x, y):
        for i, r in enumerate(self.rects):
            if r.contains(x, y):
                self.sel = i

    def mouse_press(self, x, y):
        for i, r in enumerate(self.rects):
            if r.contains(x, y):
                self.choose(i)

    def choose(self, i):
        gp, kind = self.gp, self.keys[i]
        gp.flags.add("decision_" + kind)
        gp.flags.add("decision")
        gp.save_progress()
        self.audio.play("thud")
        gp.frozen = False
        self.game.pop()
        from .ending import EndingScene
        self.game.push(EndingScene(self.game, gp, kind))

    def draw(self, p):
        t = self.t
        p.save()
        ui.overlay_open(p, t, 215)
        ui.text_spaced(p, "THE LAST DECISION", W / 2, 34, AMBER, 13, 4, True, True)
        for j, ln in enumerate(DECISION_INTRO):
            for k, wl in enumerate(ui.wrap(ln, 400, 8)):
                ui.text(p, wl, W / 2 - 200, 56 + j * 24 + k * 11, TEXT, 8)
        for i, r in enumerate(self.rects):
            kind = self.keys[i]
            title, desc = DECISION[kind]
            col = QColor(255, 210, 120) if kind == "warn" else QColor(120, 190, 255)
            on = i == self.sel
            p.fillRect(r, QColor(col.red() // 8, col.green() // 8, col.blue() // 8, 235))
            if on:
                p.fillRect(QRectF(r.x() - 2, r.y() - 2, r.width() + 4, r.height() + 4), QColor(col.red(), col.green(), col.blue(), int(40 + 30 * math.sin(t * 6))))
            p.setPen(QPen(col if on else DIM, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(r.x() + .5, r.y() + .5, r.width() - 1, r.height() - 1))
            ui.text(p, ("> " + title + " <") if on else title, r.center().x(), r.y() + 18, col if on else TEXT, 9, True, True, on)
            for k, wl in enumerate(ui.wrap(desc, int(r.width()) - 24, 7)):
                ui.text(p, wl, r.x() + 12, r.y() + 36 + k * 10, TEXT if on else DIM, 7)
        ui.text(p, "A / D choose     ENTER decide     ESC not yet", W / 2, H - 10, DIM, 7, False, True)
        p.restore()
