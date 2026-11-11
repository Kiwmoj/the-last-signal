"""Main menu with an animated procedural background."""
import math
import random
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPolygonF, QRadialGradient, QBrush

from ..constants import W, H, CYAN, AMBER, TEXT, DIM
from ..engine import Scene
from .. import ui


class MenuScene(Scene):
    ITEMS = ["Play", "How to Play", "Your Mission", "Settings", "Credits", "Quit"]

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
        prog = self.game.save.data.get("progress")
        has_save = bool(prog) and prog.get("v") == 2        # older, pre-story saves cannot be resumed
        first = ["Continue", "New Game"] if has_save else ["Play"]
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
        if name in ("Play", "Continue", "New Game"):
            from .gameplay import GameplayScene
            if name == "Continue":
                self.game.push(GameplayScene(self.game, load=True))
            else:
                if name == "New Game":
                    self.game.save.data["progress"] = None
                    self.game.save.save()
                from .intro import IntroScene
                self.game.push(IntroScene(self.game))
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
            y = 120 + i * 17
            on = i == self.sel % len(self.items())
            col = AMBER if on else TEXT
            label = f"> {name} <" if on else name
            ui.text(p, label, W / 2, y, col, 11, on, True, on)
        prog = self.game.save.data.get("progress")
        if prog and prog.get("v") == 2 and self.items()[self.sel % len(self.items())] == "Continue":
            ui.text(p, "Chapter " + str(prog.get("chapter", 1)) + ":  " + prog.get("objective", "..."), W / 2, 232, DIM, 7, False, True)
        seen = self.game.save.data.get("endings", [])
        if seen:
            ui.text(p, f"Endings found: {len(set(seen))}/2", W - 8 - 80, 14, DIM, 7)
        ui.text(p, "W/S select   ENTER confirm   F11 fullscreen",
                W / 2, H - 8, DIM, 7, False, True)


_star_cache = []


def _stars():
    if not _star_cache:
        rnd = random.Random(7)
        _star_cache.extend((rnd.randint(0, W), rnd.randint(0, 170), rnd.random() * 6)
                           for _ in range(90))
    return _star_cache


def draw_backdrop(p, t):
    """Night sky, ridge line and a blinking radio tower."""
    for x, y, ph in _stars():
        a = 120 + 100 * math.sin(t * 1.5 + ph)
        p.fillRect(x, y, 1, 1, QColor(200, 220, 255, int(a)))
    pts = [QPointF(0, H)]
    for x in range(0, W + 8, 8):
        pts.append(QPointF(x, 205 + 12 * math.sin(x * .02) + 6 * math.sin(x * .07)))
    pts.append(QPointF(W, H))
    p.setBrush(QColor(10, 14, 24))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(QPolygonF(pts))
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
