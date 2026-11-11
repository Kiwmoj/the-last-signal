"""Credits screen."""
from ..constants import W, CYAN, TEXT, DIM
from ..engine import Scene
from .. import ui
from .menu import draw_backdrop


class CreditsScene(Scene):
    LINES = [("THE LAST SIGNAL", CYAN),
             ("Game jam entry", TEXT),
             ("Design, code & procedural art: you", TEXT),
             ("Built with Python + PyQt6 + QPainter", TEXT),
             ("No external assets - everything is drawn in code", DIM)]

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def key_press(self, k):
        self.game.pop()

    def draw(self, p):
        draw_backdrop(p, self.t)
        ui.panel(p, 70, 50, 340, 150, CYAN)
        ui.text(p, "CREDITS", W / 2, 75, CYAN, 12, True, True, True)
        for i, (s, c) in enumerate(self.LINES):
            ui.text(p, s, W / 2, 100 + i * 14, c, 8, False, True)
        ui.text(p, "press any key", W / 2, 190, DIM, 7, False, True)
