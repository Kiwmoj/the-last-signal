"""Pause menu overlay: resume, save, settings, quit to menu."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..constants import W, H, CYAN, AMBER, TEXT, DIM, GREEN
from ..engine import Scene
from .. import ui


class PauseScene(Scene):
    overlay = True   # engine keeps drawing the gameplay scene underneath
    pauses_music = True
    ITEMS = ["Resume", "How to Play", "Your Mission", "Journal", "Save Game", "Settings", "Quit to Menu"]

    def __init__(self, game, gameplay):
        super().__init__(game)
        self.gp = gameplay
        self.sel = 0
        self.msg = ""
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def key_press(self, k):
        K = Qt.Key
        if k == K.Key_Escape:
            self.game.pop()
        elif k == K.Key_M:
            self.quit_to_menu()
        elif k in (K.Key_W, K.Key_Up):
            self.sel = (self.sel - 1) % len(self.ITEMS)
        elif k in (K.Key_S, K.Key_Down):
            self.sel = (self.sel + 1) % len(self.ITEMS)
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space):
            name = self.ITEMS[self.sel]
            if name == "Resume":
                self.game.pop()
            elif name == "How to Play":
                from .howto import HowToScene
                self.game.push(HowToScene(self.game, from_pause=True))
            elif name == "Your Mission":
                from .mission import MissionScene
                self.game.push(MissionScene(self.game, from_pause=True))
            elif name == "Journal":
                from .journal import JournalScene
                self.game.push(JournalScene(self.game, self.gp))
            elif name == "Save Game":
                self.gp.save_progress()
                self.msg = "Progress saved."
            elif name == "Settings":
                from .settings import SettingsScene
                self.game.push(SettingsScene(self.game))
            else:
                self.quit_to_menu()

    def quit_to_menu(self):
        """Save, then go back to the main menu no matter how the game was started."""
        from .menu import MenuScene
        self.gp.save_progress()
        self.game.audio.set_hum(0)
        menu = next((s for s in self.game.scenes if isinstance(s, MenuScene)), None) or MenuScene(self.game)
        self.game.scenes[:] = [menu]

    def draw(self, p):
        p.fillRect(0, 0, W, H, QColor(0, 0, 8, 160))
        ui.panel(p, 150, 42, 180, 190, CYAN)
        ui.text(p, "PAUSED", W / 2, 66, CYAN, 12, True, True, True)
        for i, name in enumerate(self.ITEMS):
            on = i == self.sel
            ui.text(p, f"> {name} <" if on else name, W / 2, 92 + i * 18,
                    AMBER if on else TEXT, 9, on, True, on)
        ui.text(p, self.msg or "ESC resume    M main menu", W / 2, 222, GREEN if self.msg else DIM, 7, False, True)
