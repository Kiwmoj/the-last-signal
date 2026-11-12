"""Settings screen: music volume, sound effects volume, scanlines, fullscreen. Persisted via SaveData."""
from PyQt6.QtCore import Qt

from ..constants import W, CYAN, AMBER, TEXT, DIM
from ..engine import Scene
from .. import ui
from .menu import draw_backdrop


class SettingsScene(Scene):
    previews_music = True        # opened from the pause menu the music is audible again, so the slider can be heard

    def __init__(self, game):
        super().__init__(game)
        self.sel = 0
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def rows(self):
        s = self.game.save.settings
        bar = lambda v: "|" * v + "." * (10 - v)
        return [
            f"Music       {bar(s['music_volume'])}",
            f"Effects     {bar(s['sfx_volume'])}",
            f"Guide arrows {'ON' if s.get('guide_arrows', True) else 'OFF'}",
            f"Scanlines   {'ON' if s['scanlines'] else 'OFF'}",
            f"Fullscreen  {'ON' if s['fullscreen'] else 'OFF'}",
            "Controls...",
            "Back",
        ]

    def key_press(self, k):
        K, s = Qt.Key, self.game.save.settings
        n = len(self.rows())
        arrows = (K.Key_A, K.Key_Left, K.Key_D, K.Key_Right)
        if k in (K.Key_W, K.Key_Up):
            self.sel = (self.sel - 1) % n
        elif k in (K.Key_S, K.Key_Down):
            self.sel = (self.sel + 1) % n
        elif k in arrows + (K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space):
            d = -1 if k in (K.Key_A, K.Key_Left) else 1
            if self.sel == 0:
                s["music_volume"] = max(0, min(10, s["music_volume"] + d))
            elif self.sel == 1:
                s["sfx_volume"] = max(0, min(10, s["sfx_volume"] + d))
                self.game.audio.play("blip")             # hear the new effects volume straight away
            elif self.sel == 2:
                s["guide_arrows"] = not s.get("guide_arrows", True)
            elif self.sel == 3:
                s["scanlines"] = not s["scanlines"]
            elif self.sel == 4:
                self.game.set_fullscreen(not s["fullscreen"])
            elif self.sel == 5:
                if k not in arrows:
                    from .controls import ControlsScene
                    self.game.push(ControlsScene(self.game))
            elif k not in arrows:
                self.close()
        elif k == K.Key_Escape:
            self.close()

    def close(self):
        self.game.save.save()
        self.game.pop()

    def draw(self, p):
        draw_backdrop(p, self.t)
        ui.panel(p, 110, 38, 260, 196, CYAN)
        ui.text(p, "SETTINGS", W / 2, 60, CYAN, 12, True, True, True)
        for i, r in enumerate(self.rows()):
            on = i == self.sel
            ui.text(p, ("> " if on else "  ") + r, 128, 84 + i * 18,
                    AMBER if on else TEXT, 9, on)
        ui.text(p, "A/D adjust   ESC back", W / 2, 224, DIM, 7, False, True)
