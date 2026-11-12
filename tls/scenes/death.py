"""Game over: the Unknown took you. RETRY brings you back on 88.1 right where you stood (progress is never lost); MAIN MENU saves and leaves."""
import math
import random
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPen

from ..constants import W, H, AMBER, TEXT, DIM, RED
from .. import ui
from .overlay import Overlay, Typer

LINES = ["Your headset screams. The static is not noise any more. It is a voice, and it has your name.",
         "The Unknown keeps what listens too long."]


class DeathScene(Overlay):
    live = False

    def __init__(self, game, gp):
        super().__init__(game, gp)
        self.sel = 0
        self.typer = Typer(" ".join(LINES), 40)
        self.rects = [QRectF(110, 196, 120, 24), QRectF(250, 196, 120, 24)]
        self.labels = ["TRY AGAIN", "MAIN MENU"]
        self.audio.play("static", .9)
        self.audio.play("thud", .8)
        self.rnd = random.Random(4)

    def tick(self, dt):
        self.audio.set_music(.25)
        if self.typer.update(dt):
            self.audio.play(random.choice(("voice_a", "voice_b", "voice_c")), .4)

    def key_press(self, k):
        K = Qt.Key
        if self.t < .8:
            return
        if k in (K.Key_A, K.Key_Left, K.Key_D, K.Key_Right):
            self.sel = 1 - self.sel
            self.audio.play("click", .4)
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space):
            self.choose(self.sel)

    def mouse_move(self, x, y):
        for i, r in enumerate(self.rects):
            if r.contains(x, y):
                self.sel = i

    def mouse_press(self, x, y):
        if self.t < .8:
            return
        for i, r in enumerate(self.rects):
            if r.contains(x, y):
                self.choose(i)

    def choose(self, i):
        gp = self.gp
        if i == 0:
            self.game.pop()
            gp.respawn()
        else:
            gp.save_progress()
            from .menu import MenuScene
            self.audio.set_hum(0)
            menu = next((s for s in self.game.scenes if isinstance(s, MenuScene)), None) or MenuScene(self.game)
            self.game.scenes[:] = [menu]

    def draw(self, p):
        t = self.t
        a = min(1.0, t / .9)
        p.save()
        p.fillRect(0, 0, W, H, QColor(6, 0, 10, int(235 * a)))
        for _ in range(int(12 * a)):                                   # tearing static
            y = self.rnd.randint(0, H - 4)
            g = self.rnd.randint(40, 120)
            p.fillRect(self.rnd.randint(0, W // 2), y, self.rnd.randint(40, 200), self.rnd.randint(1, 3), QColor(g, 20, g + 40, 90))
        shake = int(math.sin(t * 60) * 2 * max(0.0, 1 - t / .8))
        ui.text_spaced(p, "SIGNAL LOST", W / 2 + shake, 84, QColor(255, 70, 110, int(255 * a)), 20, 6, True, True)
        for j, ln in enumerate(ui.wrap(self.typer.text[:int(self.typer.shown)], 360, 8)):
            ui.text(p, ln, W / 2 - 180, 116 + j * 12, QColor(200, 190, 215, int(255 * a)), 8)
        if t > .8:
            for i, r in enumerate(self.rects):
                on = i == self.sel
                p.fillRect(r, QColor(60, 20, 50, 235) if on else QColor(20, 10, 24, 220))
                p.setPen(QPen(AMBER if on else DIM, 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(QRectF(r.x() + .5, r.y() + .5, r.width() - 1, r.height() - 1))
                ui.text(p, ("> " + self.labels[i] + " <") if on else self.labels[i], r.center().x(), r.y() + 16, AMBER if on else TEXT, 9, True, True, on)
            n = self.gp.deaths
            ui.text(p, f"Lost to the Unknown: {n} time{'s' if n != 1 else ''}.  Your progress is saved.", W / 2, 240, DIM, 7, False, True)
        p.restore()
