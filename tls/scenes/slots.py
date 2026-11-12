"""Save slots: pick one of three slots to load a game, or to start a new one (asks before overwriting).

W/S choose, ENTER confirms, DEL deletes a slot (press twice), ESC goes back. Mouse: click a slot.
"""
import math
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPen

from ..constants import W, H, CYAN, AMBER, TEXT, DIM, GREEN, RED
from ..engine import Scene
from ..save import SLOTS
from .. import ui
from .menu import draw_backdrop


class SlotScene(Scene):
    def __init__(self, game, mode):
        super().__init__(game)
        self.mode = mode                       # "load" or "new"
        self.sel = game.save.data["slot"]
        self.t = 0.0
        self.confirm = None                    # ("overwrite" | "delete", slot) waiting for a second press
        self.msg = ""
        self.rects = [QRectF(60, 70 + i * 46, 360, 40) for i in range(SLOTS)]

    def update(self, dt):
        self.t += dt
        self.game.audio.set_music(.8)

    def prog(self, i):
        p = self.game.save.data["slots"][i]
        return p if p and p.get("v") == 2 else None

    def key_press(self, k):
        K = Qt.Key
        if k == K.Key_Escape:
            self.game.pop()
        elif k in (K.Key_W, K.Key_Up):
            self.sel, self.confirm, self.msg = (self.sel - 1) % SLOTS, None, ""
        elif k in (K.Key_S, K.Key_Down):
            self.sel, self.confirm, self.msg = (self.sel + 1) % SLOTS, None, ""
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space):
            self.activate(self.sel)
        elif k in (K.Key_Delete, K.Key_Backspace, K.Key_X):
            self.delete(self.sel)

    def mouse_move(self, x, y):
        for i, r in enumerate(self.rects):
            if r.contains(x, y):
                self.sel = i

    def mouse_press(self, x, y):
        for i, r in enumerate(self.rects):
            if r.contains(x, y):
                self.sel = i
                self.activate(i)

    def activate(self, i):
        sv = self.game.save
        audio = self.game.audio
        if self.mode == "load":
            if not self.prog(i):
                self.msg = "That slot is empty."
                audio.play("bad", .5)
                return
            sv.select_slot(i)
            sv.save()
            from .gameplay import GameplayScene
            self.game.replace(GameplayScene(self.game, load=True))
        else:
            if self.prog(i) and self.confirm != ("overwrite", i):
                self.confirm, self.msg = ("overwrite", i), "This slot has a saved game. Press ENTER again to overwrite it."
                audio.play("bad", .5)
                return
            sv.select_slot(i)
            sv.clear_slot(i)
            sv.save()
            from .intro import IntroScene
            self.game.replace(IntroScene(self.game))

    def delete(self, i):
        if not self.prog(i):
            return
        if self.confirm != ("delete", i):
            self.confirm, self.msg = ("delete", i), "Press DEL again to delete this slot for good."
            self.game.audio.play("bad", .5)
            return
        self.game.save.clear_slot(i)
        self.game.save.save()
        self.confirm, self.msg = None, "Slot deleted."

    def draw(self, p):
        t = self.t
        draw_backdrop(p, t)
        p.fillRect(0, 0, W, H, QColor(2, 4, 10, 190))
        ui.text_spaced(p, "LOAD GAME" if self.mode == "load" else "NEW GAME: CHOOSE A SLOT", W / 2, 32, CYAN, 13, 3, True, True)
        for i, r in enumerate(self.rects):
            on = i == self.sel
            pr = self.prog(i)
            p.fillRect(r, QColor(14, 22, 38, 235) if on else QColor(10, 14, 24, 220))
            p.setPen(QPen(AMBER if on else QColor(50, 62, 84), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(r.x() + .5, r.y() + .5, r.width() - 1, r.height() - 1))
            if on:
                p.fillRect(QRectF(r.x(), r.y(), 3, r.height()), AMBER)
            ui.text(p, f"SLOT {i + 1}", r.x() + 12, r.y() + 15, AMBER if on else TEXT, 9, True)
            if pr:
                ui.text(p, f"Chapter {pr.get('chapter', 1)}", r.x() + 12, r.y() + 30, CYAN, 8, True)
                ui.text(p, pr.get("objective", "")[:46], r.x() + 80, r.y() + 30, DIM, 7)
                ui.text(p, ("ACTIVE" if i == self.game.save.data["slot"] else ""), r.right() - 56, r.y() + 15, GREEN, 7, True)
            else:
                ui.text(p, "EMPTY", r.x() + 12, r.y() + 30, DIM, 8)
        if self.msg:
            ui.text(p, self.msg, W / 2, 224, RED if self.confirm else GREEN, 8, True, True)
        ui.text(p, "W/S choose   ENTER select   DEL delete   ESC back", W / 2, H - 8, DIM, 7, False, True)
