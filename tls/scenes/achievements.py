"""Achievements page: every achievement, ticked or locked, with the overall completion percentage."""
import math
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor

from ..constants import W, H, CYAN, AMBER, TEXT, DIM, GREEN
from ..achievements import ACHIEVEMENTS, completion
from ..engine import Scene
from .. import ui
from .menu import draw_backdrop


class AchievementsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def key_press(self, k):
        if k in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_E, Qt.Key.Key_Space):
            self.game.pop()

    def draw(self, p):
        draw_backdrop(p, self.t)
        p.fillRect(0, 0, W, H, QColor(2, 4, 10, 205))
        have = set(self.game.save.data.get("achievements", []))
        ui.text_spaced(p, "ACHIEVEMENTS", W / 2, 26, CYAN, 14, 3, True, True)
        ui.text(p, f"{completion(self.game.save)}% complete   ({len(have)} of {len(ACHIEVEMENTS)})", W / 2, 38, AMBER, 8, True, True)
        for i, (aid, title, desc, _t) in enumerate(ACHIEVEMENTS):
            col, row = divmod(i, 8)
            x, y = 14 + col * 236, 48 + row * 24
            got = aid in have
            p.fillRect(x, y, 228, 21, QColor(14, 24, 40, 235) if got else QColor(10, 12, 20, 220))
            p.fillRect(x, y, 3, 21, GREEN if got else QColor(50, 56, 70))
            ui.text(p, "OK" if got else "--", x + 12, y + 14, GREEN if got else DIM, 8, True)
            ui.text(p, title if (got or aid != "nora") else "???", x + 32, y + 9, TEXT if got else DIM, 7, True)
            ui.text(p, desc[:44], x + 32, y + 18, DIM, 6)
        ui.text(p, "ESC back", W / 2, H - 8, DIM, 7, False, True)
