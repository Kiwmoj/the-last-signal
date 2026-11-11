"""Echo Receiver interface (R). The handheld is drawn big on the left; its three physical buttons
select the mode and the expanded display on the right shows the readout.

  SCAN   - sweeps all three bands from where you stand and says which one hides something near you
  TRACK  - arrow + strength toward the nearest hidden thing on the tuned band; also turns on the HUD
           tracker and reveals hidden signal sources in the world
  MEMORY - replay every recording you have found

Q / SPACE keep tuning the radio exactly as in the world, and the world keeps animating behind the
dimmed screen so tuning from in here is visible.
"""
import math
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPen

from ..constants import CYAN, AMBER, TEXT, DIM, GREEN, RED
from ..echo import draw_device
from ..story import REWARD
from ..world import FREQS, FREQ_NAMES, TINT
from .. import ui
from .overlay import Overlay, Typer, elide

MODES = ("SCAN", "TRACK", "MEMORY")
BTN = ((255, 176, 60), (80, 230, 255), (90, 255, 150))


class EchoScene(Overlay):
    def __init__(self, game, gp):
        super().__init__(game, gp)
        self.mode = 0
        self.sel = 0
        self.ping = 0.0
        self.smooth = [0.0, 0.0, 0.0]
        self.play = None            # (title, band, Typer) while a recording is being replayed
        self.msg, self.msg_t = "", 0.0
        gp.flags.add("echo_opened")
        self.audio.play("scan")

    def say(self, s, secs=2.5):
        self.msg, self.msg_t = s, secs

    # ------------------------------------------------------------------ logic
    def tick(self, dt):
        gp = self.gp
        self.ping = max(0.0, self.ping - dt * .8)
        self.msg_t = max(0.0, self.msg_t - dt)
        for b in range(3):
            self.smooth[b] += (gp.strength(b) - self.smooth[b]) * min(1.0, dt * 5)
        if self.play and self.play[2].update(dt):
            self.audio.play("blip", .35)

    def set_mode(self, m):
        if m != self.mode:
            self.mode = m
            self.play = None
            self.audio.play("click")

    def key_press(self, k):
        K, gp = Qt.Key, self.gp
        if k in (K.Key_Escape, K.Key_R):
            self.audio.play("click")
            self.close()
        elif self.tune_key(k):
            pass
        elif k in (K.Key_1, K.Key_2, K.Key_3):
            self.set_mode(int(k) - int(K.Key_1))
        elif k in (K.Key_A, K.Key_Left):
            self.set_mode((self.mode - 1) % 3)
        elif k in (K.Key_D, K.Key_Right):
            self.set_mode((self.mode + 1) % 3)
        elif self.mode == 2 and k in (K.Key_W, K.Key_Up, K.Key_S, K.Key_Down):
            n = len(gp.memory)
            if n:
                self.sel = (self.sel + (-1 if k in (K.Key_W, K.Key_Up) else 1)) % n
                self.audio.play("click", .4)
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E):
            self.action()

    def action(self):
        gp = self.gp
        if self.mode == 0:                       # SCAN: ping the area
            self.ping = 1.0
            self.audio.play("scan")
            if max(self.smooth) > .25:
                gp.flags.add("echo_scanned")
        elif self.mode == 1:                     # TRACK: toggle
            if "echo_track" in gp.flags:
                gp.flags.discard("echo_track")
                self.say("TRACKING OFF", 2)
            else:
                gp.flags.add("echo_track")
                self.say("TRACKING ON", 2.5)
            self.audio.play("ok" if "echo_track" in gp.flags else "click")
        else:                                    # MEMORY: replay
            ents = gp.memory.entries
            if not ents:
                self.say("Nothing recorded yet.", 2)
                self.audio.play("bad", .5)
                return
            e = ents[min(self.sel, len(ents) - 1)]
            self.play = (e["title"], int(e["cat"]), Typer(e["text"], 55))
            self.audio.play("tune")
            gp.flags.add("tut_memory")
            if "src_tut" in gp.flags:
                gp.complete("tut_done", "Echo Training", REWARD["tut_done"])

    # ------------------------------------------------------------------ drawing
    def draw(self, p):
        gp, t = self.gp, self.t
        band = gp.eff
        tint = QColor(*TINT[band])
        p.save()
        ui.overlay_open(p, t, 190)
        draw_device(p, 30, 46, 3, t, band, gp.strength(band), self.mode, gp.dial)
        ui.text(p, "ECHO RECEIVER", 96, 26, CYAN, 8, True, True, True)
        px, py, pw, ph = 176, 14, 292, 242
        ui.panel(p, px, py, pw, ph, tint)
        # mode buttons (mirrors the physical ones)
        for i, name in enumerate(MODES):
            bx = px + 8 + i * 92
            c = BTN[i]
            on = i == self.mode
            p.fillRect(bx, py + 8, 86, 17, QColor(c[0], c[1], c[2], 70) if on else QColor(18, 24, 36))
            p.setPen(QColor(*c) if on else QColor(60, 70, 90))
            p.drawRect(bx, py + 8, 85, 16)
            ui.text(p, f"{i + 1}  {name}", bx + 43, py + 20, QColor(*c) if on else DIM, 8, on, True)
        ui.text(p, f"{FREQS[band]} MHz  {FREQ_NAMES[band]}" + ("" if gp.radio_on else "  (radio off)"),
                px + 8, py + 38, tint, 8, True)
        p.fillRect(px + 6, py + 43, pw - 12, 1, QColor(60, 80, 100))
        (self._scan, self._track, self._memory)[self.mode](p, px, py + 48, pw, ph - 70, tint)
        if self.msg_t > 0:
            ui.text(p, self.msg, px + pw - 10 - len(self.msg) * 7, py + ph - 18, QColor(AMBER.red(), AMBER.green(), AMBER.blue(), int(255 * min(1, self.msg_t))), 8, True)
        ui.text(p, "1/2/3 mode   ENTER act   Q tune   SPACE radio   R close", px + 8, py + ph - 7, DIM, 6)
        p.restore()

    def _scan(self, p, x, y, w, h, tint):
        gp, t = self.gp, self.t
        ui.type_lines(p, "FREQUENCY SCANNER. Sweeps all three bands from where you stand. A bright bar means something hidden "
                         "is close on that band. Tune to it with Q, then use TRACK.", 99999, x + 8, y + 4, w - 16, TEXT, 7, 9)
        best = max(range(3), key=lambda b: self.smooth[b])
        sweep = (t * .5) % 1
        for b in range(3):
            yy = y + 50 + b * 34
            c = QColor(*TINT[b])
            ui.text(p, f"{FREQS[b]}", x + 8, yy + 8, c, 9, True)
            ui.text(p, FREQ_NAMES[b], x + 8, yy + 20, DIM, 6)
            p.fillRect(x + 70, yy, 150, 14, QColor(10, 16, 26))
            s = self.smooth[b]
            p.fillRect(x + 70, yy, int(150 * s), 14, QColor(c.red(), c.green(), c.blue(), 200))
            p.fillRect(x + 70 + int(150 * sweep), yy, 1, 14, QColor(255, 255, 255, 90))
            p.setPen(QColor(60, 80, 100))
            p.drawRect(x + 70, yy, 149, 13)
            label = "CLUE DETECTED" if s > .5 else "faint trace" if s > .2 else "nothing near"
            ui.text(p, label, x + 70, yy + 26, GREEN if s > .5 else AMBER if s > .2 else DIM, 6, s > .5)
            if b == gp.eff:
                ui.text(p, "TUNED", x + 228, yy + 10, c, 7, True)
            elif b == best and s > .2:
                ui.text(p, "<- TUNE HERE", x + 224, yy + 10, GREEN, 6, True)
        if self.ping > 0:                              # radar ping
            for i in range(3):
                r = (1 - self.ping) * 60 + i * 8
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(tint.red(), tint.green(), tint.blue(), int(160 * self.ping)), 1))
                p.drawEllipse(QPointF(x + w - 36, y + 120), r * .6, r * .6)
        ui.text(p, "[ENTER] ping", x + 8, y + h - 8, AMBER, 7, True)

    def _track(self, p, x, y, w, h, tint):
        gp, t = self.gp, self.t
        on = "echo_track" in gp.flags
        band = gp.eff
        if not on:
            ui.text(p, "TRACKING OFFLINE", x + 8, y + 18, RED, 10, True, glow=True)
            ui.type_lines(p, "Press ENTER to switch tracking on. While it runs, hidden signal sources on your tuned band show up in the "
                             "world, a tracker appears on your HUD, and this screen points the way.", 99999, x + 8, y + 32, w - 16, TEXT, 7, 9)
            return
        n = gp.nearest(band)
        s = gp.strength(band)
        ui.text(p, "TRACKING ONLINE", x + 8, y + 12, GREEN, 8, True, glow=True)
        cx, cy = x + 82, y + 92
        p.setBrush(Qt.BrushStyle.NoBrush)
        for r, a in ((52, 60), (36, 90), (20, 120)):
            p.setPen(QPen(QColor(tint.red(), tint.green(), tint.blue(), a), 1))
            p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(QColor(60, 80, 100))
        p.drawLine(cx - 54, cy, cx + 54, cy); p.drawLine(cx, cy - 54, cx, cy + 54)
        if n is None:
            ui.text(p, "NO SIGNAL ON THIS BAND", cx, cy + 4, DIM, 7, True, True)
            ui.type_lines(p, "Nothing hidden is left on this band. Try another with Q.", 99999, x + 160, y + 40, w - 170, TEXT, 7, 9)
        else:
            ang = math.atan2(n[2], n[1])
            tip = QPointF(cx + math.cos(ang) * 46, cy + math.sin(ang) * 46)
            p.setPen(QPen(QColor(255, 255, 255, 240), 2))
            p.drawLine(QPointF(cx, cy), tip)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(tint)
            p.drawEllipse(tip, 4 + 3 * s, 4 + 3 * s)
            ph = (t * 1.2) % 1
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(tint.red(), tint.green(), tint.blue(), int(200 * (1 - ph) * s)), 1))
            p.drawEllipse(tip, ph * 24, ph * 24)
            ui.text(p, f"DISTANCE  {int(n[0] / 8)} m", x + 160, y + 40, TEXT, 8, True)
            ui.text(p, "STRENGTH", x + 160, y + 62, DIM, 7, True)
            lit = int(round(s * 10))
            for i in range(10):
                c = QColor(90, 255, 150) if i < 6 else QColor(255, 176, 60) if i < 9 else QColor(255, 80, 80)
                p.fillRect(x + 160 + i * 12, y + 84 - i, 10, 8 + i, c if i < lit else QColor(34, 40, 54))
            state = "SIGNAL LOCKED. Look for it nearby and press E." if s > .85 else \
                    "Getting stronger. Keep going." if s > .4 else "Weak. Follow the arrow."
            ui.type_lines(p, state, 99999, x + 160, y + 112, w - 170, GREEN if s > .85 else AMBER, 7, 9)
        ui.text(p, "[ENTER] tracking off", x + 8, y + h - 8, AMBER, 7, True)

    def _memory(self, p, x, y, w, h, tint):
        gp, t = self.gp, self.t
        ents = gp.memory.entries
        if not ents:
            ui.type_lines(p, "MEMORY is empty. Recordings you find (radio fragments, hidden signals, the beacon) are stored here "
                             "so you can replay them any time.", 99999, x + 8, y + 8, w - 16, TEXT, 7, 9)
            return
        sel = min(self.sel, len(ents) - 1)
        vis = 9
        top = max(0, min(sel - vis + 1, len(ents) - vis)) if sel >= vis else 0
        for row, e in enumerate(ents[top:top + vis]):
            i = top + row
            yy = y + 12 + row * 15
            c = QColor(*TINT[int(e["cat"])])
            if i == sel:
                p.fillRect(x + 4, yy - 10, 112, 14, QColor(50, 90, 120, 170))
            p.fillRect(x + 6, yy - 7, 2, 8, c)
            ui.text(p, elide(e["title"], 100, 6), x + 12, yy, AMBER if i == sel else TEXT, 6)
        p.fillRect(x + 120, y + 2, 1, h - 12, QColor(60, 80, 100))
        if self.play:
            title, band, ty = self.play
            c = QColor(*TINT[band])
            ui.text(p, title, x + 128, y + 12, c, 8, True, glow=True)
            ui.scope(p, x + 128, y + 18, w - 140, 24, t, c, .8 if not ty.done else .15, .08)
            ui.type_lines(p, '"' + ty.text + '"', ty.shown, x + 128, y + 58, w - 140, QColor(220, 240, 255), 7, 10,
                          glitch=.05 if band == 2 else 0.0, t=t)
        else:
            ui.type_lines(p, "Select a recording and press ENTER to replay it.", 99999, x + 128, y + 14, w - 140, DIM, 7, 9)
        ui.text(p, "W/S select   [ENTER] play", x + 8, y + h - 8, AMBER, 7, True)
