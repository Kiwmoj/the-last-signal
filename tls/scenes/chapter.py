"""Chapter cards: the cinematic transition between chapters.

Shows "CHAPTER n-1 COMPLETE" (from chapter 2 on), then the new chapter's number, title and a one-line hook that
answers "why am I here and why should I continue?". ENTER/E/SPACE skips ahead once it has had a moment to land.
"""
import math
import random
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..constants import W, H, CYAN, AMBER, TEXT, DIM
from .. import ui
from ..chapters import BY_N
from .overlay import Overlay, Typer


class ChapterScene(Overlay):
    live = False

    def __init__(self, game, gp, n, event_id):
        super().__init__(game, gp)
        self.n, self.eid = n, event_id
        self.ch = BY_N[n]
        self.prev = BY_N.get(n - 1)
        self.off = 3.0 if self.prev else 0.0           # the "chapter complete" beat comes first
        self.end = self.off + 8.4
        self.title = Typer(self.ch.title, 12)
        self.hook = Typer(self.ch.hook, 38)
        self.cues = set()
        rnd = random.Random(n)
        self.stars = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0, 6.28)) for _ in range(60)]
        self.skip = False

    def cue(self, name, when, snd):
        if self.t >= when and name not in self.cues:
            self.cues.add(name)
            self.audio.play(snd)

    def tick(self, dt):
        t, o = self.t, self.off
        self.audio.set_mood("chapter")                 # short cinematic stinger; the previous mood resumes afterwards
        self.audio.set_music(1.0)
        if self.prev:
            self.cue("done", .2, "ok")
        self.cue("rise", o + .1, "rise")
        self.cue("thud", o + .9, "thud")
        if t >= o + .9:
            if self.title.update(dt):
                self.audio.play("blip", .4)
        if t >= o + 3.4:
            self.hook.update(dt)
        if self.skip and t < self.end - 1.0:
            self.t += dt * 6                            # fast-forward to the fade-out
        if t >= self.end:
            self.gp.finish_event(self.eid)
            self.game.pop()

    def key_press(self, k):
        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_E, Qt.Key.Key_Space) and self.t > 1.5:
            self.skip = True

    def draw(self, p):
        t, o = self.t, self.off
        p.fillRect(0, 0, W, H, QColor(0, 0, 0, 255))
        for (x, y, ph) in self.stars:
            p.fillRect(int(x), int(y), 1, 1, QColor(190, 205, 235, int(40 + 50 * math.sin(t * 1.3 + ph))))
        if self.prev and t < o - .2:                    # CHAPTER n COMPLETE
            a = min(1.0, t / .6, (o - .2 - t) / .6)
            a = max(0.0, a)
            ui.text_spaced(p, f"CHAPTER {self.prev.n} COMPLETE", W / 2, H / 2 - 4, QColor(120, 255, 170, int(255 * a)), 11, 4, True, True)
            ui.text_spaced(p, self.prev.title, W / 2, H / 2 + 14, QColor(150, 170, 190, int(220 * a)), 8, 3, False)
            return
        a = min(1.0, (t - o) / .8)
        fade_out = max(0.0, min(1.0, (self.end - t) / .8))
        a = max(0.0, min(a, fade_out))
        ui.text_spaced(p, f"CHAPTER {self.n}", W / 2, 96, QColor(255, 176, 60, int(255 * a)), 10, 6, True)
        p.fillRect(int(W / 2 - 40 * a), 104, int(80 * a), 1, QColor(255, 176, 60, int(160 * a)))
        s = self.title.text[:int(self.title.shown)]
        ui.text_spaced(p, s, W / 2, 132, QColor(80, 230, 255, int(255 * fade_out)), 20, 4, True, True)
        hs = self.hook.text[:int(self.hook.shown)]
        y = 162
        count = 0
        for ln in ui.wrap(self.hook.text, 320, 8):
            part = hs[count:count + len(ln) + 1]
            count += len(ln) + 1
            if part.strip():
                ui.text(p, part.strip(), W / 2 - 160, y, QColor(190, 205, 220, int(230 * fade_out)), 8)
            y += 13
        if self.title.done and self.hook.done and int(t * 2) % 2 == 0 and self.t < self.end - 1:
            ui.text(p, "[ENTER] continue", W / 2 - 40, H - 14, QColor(120, 135, 155, 160), 7)
