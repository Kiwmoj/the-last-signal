"""Cinematic introduction (~30 s). Plays on a new game, skippable with SPACE or ESC.

 0.0  black, radio static creeps in
 1.8  "Some signals are never meant to be heard."   (typewriter, fades out)
 7.6  Station 09, abandoned, at night: slow push-in, letterbox bars slide in ("STATION 09 / AUGUST 1997")
11.0  an incoming transmission appears on the scope; the voice is subtitled with its speaker
16.8  the signal drops out
17.6  "UNKNOWN TRANSMISSION DETECTED" (alert tone, glitching)
21.2  hard cut to the control room: Alex Reyes walks in and turns to the camera
24.6  title card: who Alex is and why they are here
29.0  fade to black, then the playable world fades in (Chapter 1)
"""
import math
import random
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QLinearGradient, QRadialGradient, QBrush, QPolygonF, QPen

from ..constants import W, H, CYAN, AMBER, TEXT, DIM, RED
from ..engine import Scene
from ..player import Player
from .. import ui
from .overlay import Typer

T_TXT1, T_TXT1_OUT = 1.8, 6.4
T_REVEAL = 7.6
T_CAPTION = 9.2
T_WAVE = 11.0
T_MSG = 11.8
T_LOST = 16.8
T_ALERT = 17.6
T_CUT = 21.2
T_TITLE = 24.6
T_END = 30.0
BAR = 26
EMERGENCY = "Station 09... if anyone can hear this... do not open the archive... it knows you're listening."


def _lerp(a, b, u):
    return a + (b - a) * max(0.0, min(1.0, u))


class IntroScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.skipping = False
        self.skip_t = 0.0
        self.cues = set()
        self.crackle_t = 1.0
        rnd = random.Random(5)
        self.stars = [(rnd.uniform(-20, 500), rnd.uniform(0, 140), rnd.uniform(0, 6.28)) for _ in range(70)]
        self.rain = [(rnd.uniform(-40, 520), rnd.uniform(0, H), rnd.uniform(160, 260)) for _ in range(110)]
        self.line1 = Typer("Some signals are never meant to be heard.", 15)
        self.alert = Typer("UNKNOWN TRANSMISSION DETECTED", 19)
        self.msg = Typer(EMERGENCY, 22)
        self.caption = Typer("STATION 09  -  AUGUST 1997", 16)
        self.title = Typer("STATION 09", 8)
        self.when = Typer("AUGUST 1997  -  02:47 AM", 20)
        self.sub = Typer("ALEX REYES. Radio technician. Emergency assignment.", 26)
        self.pl = Player(0, 0)

    # ------------------------------------------------------------------ flow
    def key_press(self, k):
        if k in (Qt.Key.Key_Space, Qt.Key.Key_Escape) and not self.skipping:
            self.skipping = True
            self.game.audio.play("click")

    def finish(self):
        from .gameplay import GameplayScene
        self.game.audio.set_hum(0)
        self.game.replace(GameplayScene(self.game, fade_in=True))

    def cue(self, name, when, fn):
        if self.t >= when and name not in self.cues:
            self.cues.add(name)
            fn()

    def update(self, dt):
        a = self.game.audio
        self.t += dt
        t = self.t
        if self.skipping:
            self.skip_t += dt
            a.set_hum(max(0.0, .5 * (1 - self.skip_t / .6)))
            if self.skip_t >= .6:
                self.finish()
            return
        if t >= T_END:
            self.finish()
            return
        # static creeps in, sparse crackles, music swells
        a.set_hum(min(1.0, t / 2.5) * (.55 if t < T_REVEAL else .3))
        a.set_mood("menu")
        a.set_music(min(.7, max(0.0, (t - 1.0) / 8.0)) if t < T_END - 1 else max(0.0, (T_END - t)) * .5)
        self.crackle_t -= dt
        if self.crackle_t <= 0 and t < T_CUT:
            a.play("crackle", .45)
            self.crackle_t = random.uniform(.5, 1.6)
        self.cue("rise", T_WAVE - .6, lambda: a.play("rise", .7))
        self.cue("lost", T_LOST, lambda: (a.play("static", .9), a.play("thud", .4)))
        self.cue("alert", T_ALERT, lambda: (a.play("alert", .8), a.play("thud", .6)))
        self.cue("cut", T_CUT, lambda: (a.play("thud", .9), a.play("static", .8)))
        self.cue("title", T_TITLE, lambda: a.play("note"))
        if t >= T_TXT1:
            self.line1.update(dt)
        if t >= T_CAPTION:
            self.caption.update(dt)
        if t >= T_MSG and t < T_LOST:
            if self.msg.update(dt):
                a.play("blip", .3)
        if t >= T_ALERT:
            self.alert.update(dt)
        if t >= T_TITLE:
            self.title.update(dt)
        if t >= T_TITLE + .9:
            self.when.update(dt)
        if t >= T_TITLE + 2.4:
            self.sub.update(dt)

    # ------------------------------------------------------------------ drawing
    def draw(self, p):
        t = self.t
        p.fillRect(0, 0, W, H, QColor(0, 0, 0))
        # slight handheld shake while the alert fires
        shake = 0.0
        if T_ALERT <= t < T_ALERT + 1.2:
            shake = (1 - (t - T_ALERT) / 1.2) * 2.0
        p.save()
        p.translate(random.uniform(-shake, shake), random.uniform(-shake, shake))
        if t >= T_CUT:
            self._interior(p, t - T_CUT)
        elif t >= T_REVEAL:
            p.setOpacity(min(1.0, (t - T_REVEAL) / 3.5))
            self._exterior(p, t - T_REVEAL)
            p.setOpacity(1.0)
            self._transmission(p, t)
        p.restore()
        self._first_line(p, t)
        self._film(p, t)
        self._cards(p, t)
        out = 0.0
        if self.skipping:
            out = self.skip_t / .6
        elif t > T_END - 1.0:
            out = (t - (T_END - 1.0))
        elif T_CUT <= t < T_CUT + .12:
            out = 0.0
        if out > 0:
            p.fillRect(0, 0, W, H, QColor(0, 0, 0, int(255 * min(1.0, out))))
        if T_CUT <= t < T_CUT + .35:                       # hard-cut static flash
            f = 1 - (t - T_CUT) / .35
            for _ in range(int(260 * f)):
                g = random.randint(80, 255)
                p.fillRect(random.randint(0, W), random.randint(0, H), random.randint(1, 4), 1, QColor(g, g, g, 200))
        if t > 1.5 and not self.skipping:
            ui.text(p, "SPACE / ESC  skip", W - 100, H - 7, QColor(120, 135, 155, 150), 7, False, False)

    def _first_line(self, p, t):
        if not (T_TXT1 <= t < T_REVEAL + 1):
            return
        a = 1.0
        if t > T_TXT1_OUT:
            a = max(0.0, 1 - (t - T_TXT1_OUT) / 1.0)
        s = self.line1.text[:int(self.line1.shown)]
        col = QColor(200, 215, 230, int(255 * a))
        ui.text(p, s, W / 2 - len(self.line1.text) * 3.6 + 0, H / 2 + 4, col, 12, False, False, True)
        if not self.line1.done and int(t * 3) % 2 == 0:
            ui.text(p, "_", W / 2 - len(self.line1.text) * 3.6 + len(s) * 7.4, H / 2 + 4, col, 12)

    def _film(self, p, t):
        """Grain, vignette, letterbox bars, flicker."""
        if t >= T_REVEAL:
            for _ in range(90):
                g = random.randint(90, 255)
                p.fillRect(random.randint(0, W), random.randint(0, H), 1, 1, QColor(g, g, g, random.randint(8, 34)))
            gr = QRadialGradient(W / 2, H / 2, W * .65)
            gr.setColorAt(.5, QColor(0, 0, 0, 0))
            gr.setColorAt(1, QColor(0, 0, 0, 190))
            p.fillRect(0, 0, W, H, QBrush(gr))
            bar = min(BAR, (t - T_REVEAL) * 14)
            p.fillRect(0, 0, W, int(bar), QColor(0, 0, 0))
            p.fillRect(0, H - int(bar), W, int(bar), QColor(0, 0, 0))
            if random.random() < .03:
                p.fillRect(0, 0, W, H, QColor(255, 255, 255, random.randint(6, 18)))

    def _cards(self, p, t):
        if t >= T_ALERT and t < T_CUT:
            glitch = random.random() < .18
            col = QColor(255, 70, 70, 255 if (int(t * 6) % 2 or t > T_ALERT + 2) else 150)
            ox = random.randint(-3, 3) if glitch else 0
            s = self.alert.text[:int(self.alert.shown)]
            ui.text_spaced(p, s, W / 2 + ox, 124, col, 13, 2, True, True)
            if glitch:
                ui.text_spaced(p, s, W / 2 - ox, 126, QColor(80, 230, 255, 120), 13, 2, True)
            ui.text(p, "SOURCE: NONE ON RECORD", W / 2 - 60, 142, QColor(255, 120, 120, 170), 7) if self.alert.done else None
        if t >= T_TITLE:
            a = min(1.0, (t - T_TITLE) / .6)
            x = 26
            s = self.title.text[:int(self.title.shown)]
            ui.text(p, s, x, 204, QColor(210, 230, 245, int(255 * a)), 13, True, False, True)
            ui.text(p, self.when.text[:int(self.when.shown)], x, 216, QColor(255, 176, 60, int(220 * a)), 8, True)
            ui.text(p, self.sub.text[:int(self.sub.shown)], x, 228, QColor(150, 170, 190, 230), 8)
        if T_CAPTION <= t < T_WAVE + 3:                       # place and year, lower left of the exterior shot
            a = min(1.0, (t - T_CAPTION) / .5)
            if t > T_WAVE + 2:
                a *= max(0.0, 1 - (t - T_WAVE - 2))
            ui.text(p, self.caption.text[:int(self.caption.shown)], 26, 62, QColor(200, 215, 230, int(230 * a)), 8, True)

    # ------------------------------------------------------------------ the station at night
    def _transmission(self, p, t):
        if t < T_WAVE:
            return
        a = min(1.0, (t - T_WAVE) / 1.2)
        lost = t >= T_LOST
        noise = max(.12, .9 - (t - T_WAVE) * .22) if not lost else 1.0
        p.save()
        p.setOpacity(a * .95)
        x, y, w, h = 96, 186, 288, 36
        p.fillRect(x - 6, y - 14, w + 12, h + 44, QColor(2, 8, 14, 190))
        ui.scope(p, x, y, w, h, t, CYAN if not lost else QColor(120, 120, 130), .9 if not lost else .15, noise)
        ui.text(p, "INCOMING TRANSMISSION" if not lost else "[ SIGNAL LOST ]", x, y - 5, CYAN if not lost else RED, 7, True)
        ui.text(p, "104.7 MHz", x + w - 52, y - 5, DIM, 7)
        if t >= T_MSG:                                        # subtitle with speaker identification
            ui.text(p, "UNKNOWN:", x, y + h + 11, QColor(255, 176, 60), 7, True)
            ui.type_lines(p, self.msg.text, self.msg.shown, x + 48, y + h + 11, w - 50, QColor(210, 225, 240), 7, 10)
        p.restore()

    def _exterior(self, p, te):
        px = te * 1.6
        z = 1.0 + .0125 * te
        p.save()
        p.translate(W / 2, H / 2 + 6)
        p.scale(z, z)
        p.translate(-W / 2, -H / 2 - 6)
        g = QLinearGradient(0, 0, 0, 200)
        g.setColorAt(0, QColor(3, 5, 14)); g.setColorAt(1, QColor(22, 30, 58))
        p.fillRect(-60, -30, 600, 250, QBrush(g))
        p.setPen(Qt.PenStyle.NoPen)
        for (sx, sy, ph) in self.stars:
            a = 110 + 100 * math.sin(te * 1.4 + ph)
            p.fillRect(int(sx - px * .08), int(sy), 1, 1, QColor(210, 225, 255, int(a)))
        mx, my = 92 - px * .1, 56
        mg = QRadialGradient(mx, my, 46)
        mg.setColorAt(0, QColor(190, 210, 255, 120)); mg.setColorAt(1, QColor(190, 210, 255, 0))
        p.setBrush(QBrush(mg)); p.drawEllipse(QPointF(mx, my), 46, 46)
        p.setBrush(QColor(226, 234, 250)); p.drawEllipse(QPointF(mx, my), 12, 12)
        p.setBrush(QColor(190, 202, 226))
        for cx, cy, r in ((-4, -3, 3), (4, 3, 2), (2, -5, 1.5)):
            p.drawEllipse(QPointF(mx + cx, my + cy), r, r)
        for k in range(5):                                   # drifting clouds
            cx = (k * 120 + te * (4 + k) - px * .2) % 640 - 80
            p.setBrush(QColor(18, 24, 44, 150))
            p.drawEllipse(QPointF(cx, 40 + k * 17), 60, 8)
            p.drawEllipse(QPointF(cx + 30, 36 + k * 17), 40, 6)
        # parallax ridges
        for depth, base, col, amp in ((.3, 168, (10, 14, 28), 14), (.55, 186, (8, 11, 22), 10)):
            pts = [QPointF(-60, 270)]
            for x in range(-60, 560, 10):
                pts.append(QPointF(x, base + amp * math.sin((x + px * depth) * .02) + amp * .5 * math.sin((x + px * depth) * .07)))
            pts.append(QPointF(560, 270))
            p.setBrush(QColor(*col)); p.drawPolygon(QPolygonF(pts))
        # ground
        gg = QLinearGradient(0, 200, 0, 270)
        gg.setColorAt(0, QColor(10, 14, 22)); gg.setColorAt(1, QColor(4, 6, 10))
        p.fillRect(-60, 200, 600, 80, QBrush(gg))
        ox = -px
        # the station building
        bx, by = 130 + ox, 150
        p.setBrush(QColor(20, 24, 36)); p.drawRect(int(bx), by, 150, 56)
        p.setBrush(QColor(14, 17, 26)); p.drawPolygon(QPolygonF([QPointF(bx - 8, by), QPointF(bx + 158, by), QPointF(bx + 140, by - 18), QPointF(bx + 10, by - 18)]))
        p.fillRect(int(bx + 8), by - 24, 12, 8, QColor(30, 34, 46))              # chimney
        for i in range(4):                                                       # windows
            wx = bx + 12 + i * 34
            fl = 1.0 if i != 2 else (.35 if math.sin(te * 17) * math.sin(te * 5.3) > .7 else .9)
            warm = QColor(int(255 * fl), int(190 * fl), int(90 * fl))
            p.fillRect(int(wx), by + 14, 20, 16, warm)
            p.fillRect(int(wx + 9), by + 14, 2, 16, QColor(18, 20, 28)); p.fillRect(int(wx), by + 21, 20, 2, QColor(18, 20, 28))
            sg = QRadialGradient(wx + 10, by + 28, 40)
            sg.setColorAt(0, QColor(255, 190, 90, int(60 * fl))); sg.setColorAt(1, QColor(255, 190, 90, 0))
            p.setBrush(QBrush(sg)); p.drawEllipse(QPointF(wx + 10, by + 34), 40, 26)
            p.setBrush(QColor(20, 24, 36))
        p.fillRect(int(bx + 62), by + 30, 26, 26, QColor(8, 10, 16))
        p.fillRect(int(bx + 66), by + 34, 18, 22, QColor(70, 40, 20))              # door
        ui.text(p, "STATION 09", bx + 52, by + 44, QColor(150, 160, 180, 150), 6)
        # radio tower with a pulsing beacon and signal rings
        tx = 350 + ox
        p.setPen(QPen(QColor(34, 42, 58), 1))
        for dx in (-9, 9):
            p.drawLine(QPointF(tx + dx, 206), QPointF(tx, 62))
        for i in range(1, 9):
            yy = 206 - i * 16
            w = 9 * (1 - i / 9.5)
            p.drawLine(QPointF(tx - w, yy), QPointF(tx + w, yy))
            p.drawLine(QPointF(tx - w, yy), QPointF(tx + w * .6, yy - 16))
        pulse = (math.sin(te * 3) + 1) / 2
        bg = QRadialGradient(tx, 60, 16)
        bg.setColorAt(0, QColor(255, 60, 60, int(110 + 140 * pulse))); bg.setColorAt(1, QColor(255, 60, 60, 0))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(bg)); p.drawEllipse(QPointF(tx, 60), 16, 16)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(3):
            ph = (te * .4 + i / 3) % 1
            p.setPen(QPen(QColor(80, 230, 255, int(130 * (1 - ph))), 1))
            p.drawEllipse(QPointF(tx, 60), 8 + ph * 90, (8 + ph * 90) * .55)
        p.setPen(Qt.PenStyle.NoPen)
        # fence posts in the foreground, parallaxed hard
        fx = -px * 1.7
        p.setBrush(QColor(3, 4, 8))
        for i in range(-2, 14):
            xx = (i * 46 + fx) % 620 - 70
            p.drawRect(int(xx), 214, 3, 48)
        p.drawRect(-60, 226, 620, 2); p.drawRect(-60, 240, 620, 2)
        # drifting fog
        for k in range(3):
            fx2 = (te * (6 + 3 * k) + k * 190) % 700 - 180
            fg = QLinearGradient(fx2, 0, fx2 + 300, 0)
            fg.setColorAt(0, QColor(150, 170, 200, 0)); fg.setColorAt(.5, QColor(150, 170, 200, 22)); fg.setColorAt(1, QColor(150, 170, 200, 0))
            p.fillRect(int(fx2), 190 + k * 14, 300, 26, QBrush(fg))
        # rain
        p.setPen(QPen(QColor(150, 180, 230, 80), 1))
        for (rx, ry, sp) in self.rain:
            yy = (ry + te * sp) % (H + 20) - 10
            xx = (rx - te * 26) % 560 - 40
            p.drawLine(QPointF(xx, yy), QPointF(xx - 2, yy + 7))
        p.restore()

    # ------------------------------------------------------------------ interior: meet the operator
    def _interior(self, p, tc):
        z = 1.0 + .01 * tc
        p.save()
        p.translate(W / 2, H / 2)
        p.scale(z, z)
        p.translate(-W / 2 - tc * 1.5, -H / 2)
        g = QLinearGradient(0, 0, 0, 180)
        g.setColorAt(0, QColor(6, 8, 14)); g.setColorAt(1, QColor(18, 22, 34))
        p.fillRect(-60, -20, 640, 200, QBrush(g))
        p.fillRect(-60, 176, 640, 120, QColor(10, 12, 18))
        p.setPen(QColor(24, 28, 42))
        for x in range(-60, 580, 40):
            p.drawLine(x, 40, x, 176)
        for i in range(8):                                                   # floor perspective lines
            p.drawLine(QPointF(240 + (i - 3.5) * 8, 176), QPointF(240 + (i - 3.5) * 90, 290))
        # window with rain and a moonlight shaft
        p.fillRect(46, 44, 96, 92, QColor(4, 6, 12))
        wg = QLinearGradient(0, 48, 0, 132)
        wg.setColorAt(0, QColor(6, 10, 28)); wg.setColorAt(1, QColor(22, 32, 62))
        p.fillRect(50, 48, 88, 84, QBrush(wg))
        p.setBrush(QColor(210, 222, 245)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(112, 72), 8, 8)
        p.setPen(QPen(QColor(150, 180, 230, 90), 1))
        for k in range(14):
            xx = 50 + (k * 29) % 88
            yy = 48 + ((tc * 120 + k * 37) % 90)
            p.drawLine(int(xx), int(yy), int(xx - 1), int(yy + 5))
        p.fillRect(92, 48, 2, 84, QColor(8, 10, 16)); p.fillRect(50, 88, 88, 2, QColor(8, 10, 16))
        p.setPen(Qt.PenStyle.NoPen)
        sg = QLinearGradient(0, 132, 0, 230)
        sg.setColorAt(0, QColor(130, 160, 255, 60)); sg.setColorAt(1, QColor(130, 160, 255, 0))
        p.setBrush(QBrush(sg))
        p.drawPolygon(QPolygonF([QPointF(50, 132), QPointF(138, 132), QPointF(230, 250), QPointF(120, 250)]))
        # racks and the glowing console
        for rx in (170, 202):
            p.setBrush(QColor(12, 15, 24)); p.drawRect(rx, 70, 28, 106)
            for u in range(7):
                on = math.sin(tc * (2 + u * .6) + rx) > .1
                p.fillRect(rx + 4, 78 + u * 14, 3, 2, QColor(90, 255, 150) if on else QColor(20, 40, 34))
        p.setBrush(QColor(26, 32, 46)); p.drawRect(268, 138, 190, 40)
        p.fillRect(268, 138, 190, 2, QColor(90, 104, 134))
        for i, col in enumerate(((80, 230, 255), (90, 255, 150), (255, 176, 60))):
            sx = 282 + i * 58
            p.fillRect(sx, 106, 44, 30, QColor(6, 10, 14))
            p.fillRect(sx + 2, 108, 40, 26, QColor(col[0] // 8, col[1] // 8, col[2] // 8))
            p.setPen(QPen(QColor(*col), 1))
            for k in range(40):
                v = 6 * math.sin(tc * 6 + k * .5 + i) * math.sin(tc + k * .13)
                p.drawPoint(sx + 2 + k, int(121 + v))
            p.setPen(Qt.PenStyle.NoPen)
            glow = QRadialGradient(sx + 22, 122, 60)
            glow.setColorAt(0, QColor(col[0], col[1], col[2], 70)); glow.setColorAt(1, QColor(col[0], col[1], col[2], 0))
            p.setBrush(QBrush(glow)); p.drawEllipse(QPointF(sx + 22, 126), 60, 50)
        # the operator
        pl = self.pl
        walk_end = 3.2
        x = _lerp(-26, 196, (tc - .4) / (walk_end - .4))
        moving = .4 < tc < walk_end
        pl.moving = moving
        pl.anim += 1 / 60 if moving else 0
        pl.facing = "right" if tc < 4.4 else "down"
        p.save()
        p.translate(x, 226)
        p.scale(4, 4)
        pl.x = pl.y = 0
        pl.draw(p, tc)
        p.restore()
        cg = QRadialGradient(x + 20, 190, 110)
        cg.setColorAt(0, QColor(80, 230, 255, 34)); cg.setColorAt(1, QColor(80, 230, 255, 0))
        p.setBrush(QBrush(cg)); p.drawEllipse(QPointF(x + 20, 190), 110, 90)
        p.restore()
