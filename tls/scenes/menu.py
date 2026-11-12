"""Main menu with an animated procedural background."""
import math
import random
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPolygonF, QRadialGradient, QBrush

from ..constants import W, H, CYAN, AMBER, TEXT, DIM
from ..engine import Scene
from .. import ui


class MenuScene(Scene):
    ITEMS = ["Play", "How to Play", "Your Mission", "Achievements", "Settings", "Credits", "Quit"]

    def __init__(self, game):
        super().__init__(game)
        self.sel = 0
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        self.game.audio.set_mood("menu")
        self.game.audio.set_music(1.0)
        self.game.audio.set_hum(0)

    def items(self):
        has_save = self.game.save.has_any_save()            # older, pre-story saves cannot be resumed
        first = ["Continue", "New Game", "Load Game"] if has_save else ["Play"]
        return first + self.ITEMS[1:]

    def key_press(self, k):
        K = Qt.Key
        n = len(self.items())
        self.sel %= n
        if k in (K.Key_W, K.Key_Up):
            self.sel = (self.sel - 1) % n
        elif k in (K.Key_S, K.Key_Down):
            self.sel = (self.sel + 1) % n
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space):
            self.choose()

    def choose(self):
        name = self.items()[self.sel % len(self.items())]
        if name in ("Play", "Continue"):
            from .gameplay import GameplayScene
            if name == "Continue":
                prog = self.game.save.data.get("progress")
                if not (prog and prog.get("v") == 2):          # active slot is empty: open the slot list instead
                    from .slots import SlotScene
                    self.game.push(SlotScene(self.game, "load"))
                    return
                self.game.push(GameplayScene(self.game, load=True))
            else:
                self.game.save.select_slot(0)
                self.game.save.clear_slot(0)
                self.game.save.save()
                from .intro import IntroScene
                self.game.push(IntroScene(self.game))
        elif name in ("New Game", "Load Game"):
            from .slots import SlotScene
            self.game.push(SlotScene(self.game, "new" if name == "New Game" else "load"))
        elif name == "Achievements":
            from .achievements import AchievementsScene
            self.game.push(AchievementsScene(self.game))
        elif name == "How to Play":
            from .howto import HowToScene
            self.game.push(HowToScene(self.game))
        elif name == "Your Mission":
            from .mission import MissionScene
            self.game.push(MissionScene(self.game))
        elif name == "Settings":
            from .settings import SettingsScene
            self.game.push(SettingsScene(self.game))
        elif name == "Credits":
            from .credits import CreditsScene
            self.game.push(CreditsScene(self.game))
        else:
            self.game.close()

    def draw(self, p):
        draw_backdrop(p, self.t)
        ui.text(p, "THE LAST SIGNAL", W / 2, 70, CYAN, 26, True, True, True)
        ui.text(p, "- a radio mystery -", W / 2, 88, DIM, 8, False, True)
        for i, name in enumerate(self.items()):
            y = 106 + i * 15
            on = i == self.sel % len(self.items())
            col = AMBER if on else TEXT
            label = f"> {name} <" if on else name
            ui.text(p, label, W / 2, y, col, 10, on, True, on)
        prog = self.game.save.data.get("progress")
        if prog and prog.get("v") == 2 and self.items()[self.sel % len(self.items())] == "Continue":
            ui.text(p, f"Slot {self.game.save.data['slot'] + 1}  -  Chapter " + str(prog.get("chapter", 1)) + ":  " + prog.get("objective", "..."),
                    W / 2, 248, DIM, 7, False, True)
        seen = self.game.save.data.get("endings", [])
        if seen:
            from ..story import endings_total
            ui.text(p, f"Endings found: {len(set(seen))}/{endings_total(seen)}", W - 8 - 80, 14, DIM, 7)
        ui.text(p, "W/S select   ENTER confirm   F11 fullscreen",
                W / 2, H - 8, DIM, 7, False, True)


_star_cache = []


def _stars():
    if not _star_cache:
        rnd = random.Random(7)
        _star_cache.extend((rnd.randint(0, W), rnd.randint(0, 170), rnd.random() * 6)
                           for _ in range(90))
    return _star_cache


def _atmosphere(p, t):
    """Slow drifting cloud banks and an occasional shooting star, so the title screen is never still."""
    p.setPen(Qt.PenStyle.NoPen)
    for i, (y, sp, al) in enumerate(((60, 5, 16), (96, 8, 22), (130, 3, 14))):
        off = (t * sp + i * 160) % (W + 220) - 110
        for k in range(5):
            p.setBrush(QColor(60, 80, 120, al))
            p.drawEllipse(QPointF(off + k * 44 - 90, y + math.sin(k + i) * 5), 70, 10 + 4 * math.sin(t * .2 + k))
    ph = (t % 9.0)
    if ph < .8:                                         # a shooting star every nine seconds
        u = ph / .8
        sx, sy = 120 + u * 130, 20 + u * 60
        p.setPen(QColor(220, 235, 255, int(200 * (1 - u))))
        p.drawLine(QPointF(sx, sy), QPointF(sx - 18, sy - 9))


def _station(p, t):
    """The abandoned radio station on the ridge: dark roof, a few windows that flicker like failing power."""
    bx, by = 52, 188
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(8, 11, 19))
    p.drawRect(bx, by, 150, 28)
    p.drawPolygon(QPolygonF([QPointF(bx - 8, by), QPointF(bx + 75, by - 22), QPointF(bx + 158, by)]))
    p.drawRect(bx + 118, by - 30, 8, 14)
    for i in range(5):
        lit = math.sin(t * (1.1 + i * .37) + i * 2.3) * math.sin(t * 7.3 + i) > -.55 if i not in (1, 3) else (int(t * .5 + i) % 4 != 0)
        if i == 4:
            lit = math.sin(t * 23) > .2 and math.sin(t * .8) > .5       # one window is nearly dead
        c = QColor(255, 190, 90, 210) if lit else QColor(24, 28, 38)
        p.setBrush(c)
        p.drawRect(bx + 12 + i * 27, by + 8, 14, 10)
        if lit:
            g = QRadialGradient(bx + 19 + i * 27, by + 13, 22)
            g.setColorAt(0, QColor(255, 190, 90, 40))
            g.setColorAt(1, QColor(255, 190, 90, 0))
            p.setBrush(QBrush(g))
            p.drawEllipse(QPointF(bx + 19 + i * 27, by + 13), 22, 22)


def draw_backdrop(p, t):
    """Night sky, drifting clouds, the abandoned station and a blinking radio tower."""
    drift = (t * 1.5) % W                               # the whole starfield pans slowly sideways
    for x, y, ph in _stars():
        a = 120 + 100 * math.sin(t * 1.5 + ph)
        p.fillRect(int((x - drift) % W), y, 1, 1, QColor(200, 220, 255, int(a)))
    _atmosphere(p, t)
    pts = [QPointF(0, H)]
    for x in range(0, W + 8, 8):
        pts.append(QPointF(x, 205 + 12 * math.sin(x * .02) + 6 * math.sin(x * .07)))
    pts.append(QPointF(W, H))
    p.setBrush(QColor(10, 14, 24))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(QPolygonF(pts))
    _station(p, t)
    # tower with pulsing beacon + signal rings
    tx, ty = 390, 205
    p.setPen(QColor(30, 40, 55))
    for dx in (-8, 8):
        p.drawLine(tx + dx, ty, tx, ty - 90)
    for i in range(1, 8):
        yy = ty - i * 12
        w = int(8 * (1 - i / 8))
        p.drawLine(tx - w, yy, tx + w, yy)
    pulse = (math.sin(t * 3) + 1) / 2
    g = QRadialGradient(tx, ty - 92, 14)
    g.setColorAt(0, QColor(255, 60, 60, int(120 + 120 * pulse)))
    g.setColorAt(1, QColor(255, 60, 60, 0))
    p.setBrush(QBrush(g))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(tx, ty - 92), 14, 14)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(3):
        ph = (t * .5 + i / 3) % 1
        p.setPen(QColor(80, 230, 255, int(110 * (1 - ph))))
        r = 10 + ph * 70
        p.drawEllipse(QPointF(tx, ty - 92), r, r * .6)
