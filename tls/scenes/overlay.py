"""Shared base for full-screen interface overlays (terminal, journal, puzzle screens)."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics

from ..engine import Scene
from .. import ui


def elide(s, width_px, size=7):
    return QFontMetrics(ui.font(size)).elidedText(s, Qt.TextElideMode.ElideRight, int(width_px))


class Typer:
    """Minimal typewriter for text that is not part of a Dialog."""
    def __init__(self, text, speed=60.0):
        self.text, self.speed, self.shown, self._last = text, speed, 0.0, 0

    @property
    def done(self):
        return self.shown >= len(self.text)

    def finish(self):
        self.shown = len(self.text)

    def update(self, dt):
        """Returns True when a character was just typed (use it for the blip sound)."""
        self.shown = min(len(self.text), self.shown + dt * self.speed)
        n = int(self.shown)
        hit = n > self._last and n % 3 == 0
        self._last = n
        return hit


class Overlay(Scene):
    """Drawn on top of the gameplay scene. With live=True the world keeps animating behind it
    (frequency transitions, rings, particles) while the player stands still, so tuning the radio
    from inside a puzzle screen changes the world you see through the dimmed background."""
    overlay = True
    live = True

    def __init__(self, game, gp):
        super().__init__(game)
        self.gp = gp
        self.t = 0.0
        if self.live:
            gp.frozen = True

    @property
    def audio(self):
        return self.game.audio

    def update(self, dt):
        self.t += dt
        if self.live:
            self.gp.update(dt)
        self.tick(dt)

    def tick(self, dt):
        pass

    def close(self):
        self.gp.frozen = False
        self.game.pop()

    def tune_key(self, k):
        """Q cycles frequency and SPACE toggles the radio, exactly like in the world."""
        if k == Qt.Key.Key_Q:
            self.gp.cycle_radio()
            return True
        if k == Qt.Key.Key_Space:
            self.gp.toggle_radio()
            return True
        return False
