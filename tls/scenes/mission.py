"""Your Mission: what the goal is, what to do in each chapter, and how the game is won. Spoiler-light by design.

Opened from the main menu or the pause menu. ENTER/E/SPACE/ESC or the BACK button returns. If a saved game exists, the
chapters you have finished are ticked and the current one is highlighted.
"""
import math
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPen

from ..constants import W, H, CYAN, AMBER, TEXT, DIM, GREEN
from ..engine import Scene
from .. import ui
from .menu import draw_backdrop

GOAL = ("You are Alex Reyes, a radio technician sent to Station 09 in 1997. The station has been silent for "
        "17 years, yet something is transmitting tonight. Find out who, and why.")

CHAPTERS = [
    ("1", "THE ARRIVAL", "Find the Echo Receiver and learn to tune the radio.", (80, 230, 255)),
    ("2", "THE EMPTY STATION", "Search the station, restore power, open the research wing.", (255, 176, 60)),
    ("3", "THE ARCHIVE", "Rebuild the broken transmission and unlock the archive.", (90, 255, 150)),
    ("4", "THE UNKNOWN", "Follow the echoes across all three frequencies.", (190, 90, 255)),
    ("5", "THE LAST SIGNAL", "Open the chamber, rebuild the last transmission, then decide.", (255, 120, 120)),
]
WIN = "TO WIN: finish Chapter 5 by sending the final transmission and making the last choice. There are two endings."
TIPS = "Your current objective is always shown top-left. Press J for your journal."


class MissionScene(Scene):
    def __init__(self, game, from_pause=False):
        super().__init__(game)
        self.t = 0.0
        self.back = QRectF(190, 238, 100, 20)

    def current_chapter(self):
        prog = self.game.save.data.get("progress")
        return prog.get("chapter", 1) if prog and prog.get("v") == 2 else 0

    def update(self, dt):
        self.t += dt
        self.game.audio.set_music(.7)

    def key_press(self, k):
        K = Qt.Key
        if k in (K.Key_Escape, K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space):
            self.game.audio.play("click")
            self.game.pop()

    def mouse_press(self, x, y):
        if self.back.contains(x, y):
            self.game.audio.play("click")
            self.game.pop()

    def draw(self, p):
        t = self.t
        draw_backdrop(p, t)
        p.fillRect(0, 0, W, H, QColor(2, 4, 10, 200))
        ui.text_spaced(p, "YOUR MISSION", W / 2, 26, CYAN, 15, 4, True, True)
        p.fillRect(150, 32, 180, 1, QColor(80, 230, 255, 90))

        # the goal
        p.fillRect(18, 40, 444, 38, QColor(10, 16, 28, 235))
        p.fillRect(18, 40, 3, 38, AMBER)
        ui.text(p, "THE GOAL", 28, 51, AMBER, 8, True)
        for j, ln in enumerate(ui.wrap(GOAL, 420, 7)[:3]):
            ui.text(p, ln, 28, 61 + j * 8, TEXT, 7)

        # five chapters
        cur = self.current_chapter()
        for i, (num, title, goal, col) in enumerate(CHAPTERS):
            y = 84 + i * 25
            c = QColor(*col)
            here = cur == i + 1
            done = cur > i + 1
            p.fillRect(18, y, 444, 22, QColor(10, 16, 28, 230))
            p.fillRect(18, y, 3, 22, c)
            if here:
                p.fillRect(18, y, 444, 22, QColor(c.red(), c.green(), c.blue(), 22 + int(14 * math.sin(t * 4))))
            ui.text(p, "OK" if done else num, 33, y + 16, GREEN if done else c, 11 if not done else 8, True, True)
            ui.text(p, title, 48, y + 10, c, 8, True)
            ui.text(p, goal, 48, y + 19, TEXT, 7)
            if here:
                ui.text(p, "< YOU ARE HERE", 392, y + 14, c, 7, True)

        # how to win
        p.fillRect(18, 212, 444, 24, QColor(40, 14, 14, 235))
        p.fillRect(18, 212, 3, 24, QColor(255, 120, 120))
        for j, ln in enumerate(ui.wrap(WIN, 420, 7)[:2]):
            ui.text(p, ln, 28, 223 + j * 9, QColor(255, 200, 190), 7, j == 0)

        # back
        glow = int(40 + 30 * math.sin(t * 6))
        r = self.back
        p.fillRect(QRectF(r.x() - 2, r.y() - 2, r.width() + 4, r.height() + 4), QColor(80, 230, 255, glow))
        p.fillRect(r, QColor(30, 40, 60))
        p.setPen(QPen(CYAN, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(r.x() + .5, r.y() + .5, r.width() - 1, r.height() - 1))
        ui.text(p, "> BACK <", r.center().x(), r.y() + 14, QColor(255, 255, 255), 9, True, True, True)
        ui.text(p, TIPS, W / 2, H - 3, DIM, 6, False, True)
