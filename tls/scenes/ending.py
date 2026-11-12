"""The two endings, then the credits.

THE WARNING  - the player sends the corrected warning back to 1980.
THE SILENCE  - the player shuts the last transmitter down.

After the credits the story is rewound to just before the decision, so Continue lets the player see the other ending.
The endings seen are kept in the save file.
"""
import math
import random
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QLinearGradient, QBrush

from ..constants import W, H, CYAN, AMBER, TEXT, DIM
from ..story import ENDINGS, CREDITS
from .. import ui
from ..engine import Scene
from .overlay import Typer
from .intro import IntroScene


class EndingScene(Scene):
    def __init__(self, game, gp, kind):
        super().__init__(game)
        self.gp, self.kind = gp, kind
        self.title, self.col, self.pages = ENDINGS[kind]
        self.t = 0.0
        self.phase = "title"            # title -> pages -> credits -> the end
        self.pi = 0
        self.typer = Typer(self.pages[0], 26)
        self.page_age = 0.0
        self.credit_y = float(H)
        self.scene = IntroScene(game)    # reuse its night-station painter for the backdrop
        self.finished = False
        self.cues = set()

    # ------------------------------------------------------------------ flow
    def key_press(self, k):
        K = Qt.Key
        advance = k in (K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space)
        if self.phase == "pages" and advance:
            if not self.typer.done:
                self.typer.finish()
            elif self.pi + 1 < len(self.pages):
                self.pi += 1
                self.typer = Typer(self.pages[self.pi], 26)
                self.page_age = 0.0
            else:
                self.phase = "credits"
                self.t = 0.0
        elif self.phase == "title" and advance and self.t > 1.5:
            self.phase, self.t = "pages", 0.0
        elif self.phase == "credits" and (advance or k == K.Key_Escape) and self.t > 2.0:
            self.credit_y -= 60              # nudge: pressing keys speeds the roll
        elif self.phase == "end" and (advance or k == K.Key_Escape):
            self.leave()

    def update(self, dt):
        a = self.game.audio
        self.t += dt
        a.set_mood("revelation")
        a.set_music(.7 if self.phase != "end" else .3)
        a.set_hum(0)
        if "boom" not in self.cues:
            self.cues.add("boom")
            a.play("thud")
        if self.phase == "title" and self.t > 4.0:
            self.phase, self.t = "pages", 0.0
        elif self.phase == "pages":
            self.page_age += dt
            if self.typer.update(dt):
                a.play("blip", .35)
        elif self.phase == "credits":
            self.credit_y -= dt * 22
            if self.credit_y < -len(CREDITS) * 17 - 20:
                self.phase, self.t = "end", 0.0
        elif self.phase == "end" and self.t > 5.0:
            self.leave()

    def leave(self):
        """Record the ending, rewind the story to just before the decision, and return to the main menu."""
        if self.finished:
            return
        self.finished = True
        gp = self.gp
        seen = self.game.save.data.setdefault("endings", [])
        if self.kind not in seen:
            seen.append(self.kind)
        from ..achievements import check as check_achievements
        check_achievements(gp)
        gp.flags -= {"decision", "decision_warn", "decision_silence", "m_c5m4", "ch5_done"}
        gp.save_progress()
        self.game.audio.set_music(0)
        self.game.scenes[:] = [self.game.scenes[0]]

    # ------------------------------------------------------------------ drawing
    def draw(self, p):
        t = self.t
        p.fillRect(0, 0, W, H, QColor(0, 0, 0))
        base = (self.pi / max(1, len(self.pages) - 1)) if self.phase == "pages" else (1.0 if self.phase in ("credits", "end") else 0.0)
        if self.phase in ("pages", "title"):
            p.save()
            self.scene._exterior(p, 6 + t * .5 + self.pi * 2)
            p.restore()
            c = self.col
            wash = QLinearGradient(0, H, 0, 0)
            a = int(40 + 120 * base)
            if self.kind == "warn":                          # warm light floods the station
                wash.setColorAt(0, QColor(255, 220, 140, a)); wash.setColorAt(1, QColor(255, 160, 80, int(a * .3)))
            else:                                            # cold grey dawn, then quiet
                wash.setColorAt(0, QColor(150, 190, 235, a)); wash.setColorAt(1, QColor(20, 30, 60, int(a * .4)))
            p.fillRect(0, 0, W, H, QBrush(wash))
            p.fillRect(0, 0, W, 26, QColor(0, 0, 0)); p.fillRect(0, H - 26, W, 26, QColor(0, 0, 0))
        if self.phase == "title":
            a = min(1.0, t / 1.0)
            ui.text_spaced(p, self.title, W / 2, H / 2, QColor(self.col[0], self.col[1], self.col[2], int(255 * a)), 15, 4, True, True)
        elif self.phase == "pages":
            p.fillRect(0, 168, W, 70, QColor(0, 0, 8, 190))
            ui.type_lines(p, self.typer.text, self.typer.shown, 40, 188, W - 80, TEXT, 9, 13)
            if self.typer.done and int(t * 2) % 2 == 0:
                more = self.pi + 1 < len(self.pages)
                ui.text(p, "[ENTER] " + ("continue" if more else "credits"), W - 110, 234, DIM, 7)
        elif self.phase == "credits":
            self._credits(p)
        elif self.phase == "end":
            a = min(1.0, t / 1.2)
            ui.text_spaced(p, "THE END", W / 2, H / 2 - 4, QColor(self.col[0], self.col[1], self.col[2], int(255 * a)), 18, 6, True, True)
            seen = self.game.save.data.get("endings", [])
            ui.text(p, f"Endings found: {len(set(seen))} of 2", W / 2 - 52, H / 2 + 20, QColor(150, 165, 185, int(220 * a)), 8)
            from ..achievements import completion
            ui.text(p, f"Achievements: {completion(self.game.save)}% complete", W / 2 - 60, H / 2 + 32, QColor(150, 165, 185, int(220 * a)), 8)
            if len(set(seen)) < 2:
                ui.text(p, "Choose Continue to try the other decision.", W / 2 - 96, H / 2 + 46, QColor(120, 135, 155, int(200 * a)), 7)
            ui.text(p, "[ENTER] main menu", W / 2 - 40, H - 14, DIM, 7)

    def _credits(self, p):
        rnd = random.Random(2)
        for i in range(70):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H)
            p.fillRect(int(x), int(y), 1, 1, QColor(190, 205, 235, int(60 + 60 * math.sin(self.t + i))))
        y = self.credit_y
        for text, kind in CREDITS:
            if -20 < y < H + 20:
                if kind == 0 and text:
                    ui.text_spaced(p, text, W / 2, int(y), QColor(80, 230, 255), 16, 4, True, True)
                elif kind == 1:
                    ui.text_spaced(p, text, W / 2, int(y), QColor(*self.col), 9, 3, True)
                elif kind == 2:
                    ui.text(p, text, W / 2 - len(text) * 2.6, int(y), TEXT, 8)
            y += 17
