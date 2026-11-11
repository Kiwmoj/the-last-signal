"""Field journal (J): story recap, clues and documents, keys, recorded tapes, people, puzzle progress.

The header always shows the current chapter mission and its hint, so the player is never lost.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..constants import CYAN, AMBER, TEXT, DIM, GREEN
from ..chapters import CHAPTERS
from ..story import PUZZLES
from ..world import FREQS, FREQ_NAMES, TINT
from .. import ui
from .overlay import Overlay, elide

TABS = ("STORY", "CLUES", "KEYS", "TAPES", "PEOPLE", "PUZZLES")


class JournalScene(Overlay):
    live = False          # the game is paused while you read

    def __init__(self, game, gp):
        super().__init__(game, gp)
        self.tab = 0
        self.sel = [0] * len(TABS)
        self.audio.play("note")

    def chapter_state(self, ch):
        f = self.gp.flags
        if f"ch{ch.n}_done" in f:
            return "done"
        return "current" if f"ch{ch.n}" in f else "locked"

    def items(self):
        gp, name = self.gp, TABS[self.tab]
        if name == "STORY":
            marks = {"done": "[x] ", "current": "[>] ", "locked": "[ ] "}
            return [(marks[self.chapter_state(c)] + f"CH{c.n} " + (c.title.title() if self.chapter_state(c) != "locked" else "???"), c) for c in CHAPTERS]
        if name == "PUZZLES":
            return [(("[x] " if fl in gp.flags else "[ ] ") + title, fl) for (fl, title, _, _) in PUZZLES]
        if name == "TAPES":
            return [(e["title"], e) for e in gp.memory.entries]
        cat = {"CLUES": "clue", "KEYS": "key", "PEOPLE": "person"}[name]
        return [(e["title"], e) for e in gp.journal.by_cat(cat)]

    def key_press(self, k):
        K = Qt.Key
        n = len(TABS)
        if k in (K.Key_Escape, K.Key_J):
            self.audio.play("click")
            self.close()
        elif k in (K.Key_A, K.Key_Left):
            self.tab = (self.tab - 1) % n
            self.audio.play("click", .4)
        elif k in (K.Key_D, K.Key_Right):
            self.tab = (self.tab + 1) % n
            self.audio.play("click", .4)
        elif k in (K.Key_W, K.Key_Up, K.Key_S, K.Key_Down):
            m = len(self.items())
            if m:
                self.sel[self.tab] = (self.sel[self.tab] + (-1 if k in (K.Key_W, K.Key_Up) else 1)) % m
                self.audio.play("click", .4)

    def draw(self, p):
        gp, t = self.gp, self.t
        p.save()
        ui.overlay_open(p, t, 200)
        x, y, w, h = 22, 14, 436, 242
        ui.panel(p, x, y, w, h, CYAN)
        ui.text(p, "FIELD JOURNAL", x + 12, y + 18, CYAN, 10, True, glow=True)
        ui.text(p, f"{len(gp.journal)} entries   {sum(1 for pz in PUZZLES if pz[0] in gp.flags)}/{len(PUZZLES)} puzzles", x + w - 150, y + 17, DIM, 7)
        for i, name in enumerate(TABS):
            on = i == self.tab
            tx = x + 8 + i * 70
            p.fillRect(tx, y + 26, 66, 14, QColor(30, 70, 90, 200) if on else QColor(14, 20, 32))
            ui.text(p, name, tx + 33, y + 37, AMBER if on else DIM, 7, on, True)
        p.fillRect(x + 8, y + 42, w - 16, 1, QColor(60, 90, 110))
        ui.text(p, "NOW", x + 12, y + 55, DIM, 6, True)
        ui.text(p, gp.objective(), x + 36, y + 55, GREEN, 8, True)
        ui.text(p, gp.hint(), x + 36, y + 66, DIM, 6)
        p.fillRect(x + 8, y + 70, w - 16, 1, QColor(60, 90, 110))

        items = self.items()
        sel = min(self.sel[self.tab], max(0, len(items) - 1))
        name = TABS[self.tab]
        if not items:
            ui.type_lines(p, {"TAPES": "No recordings yet. The Echo Receiver stores what it hears: radio fragments, hidden signals and more.",
                              "PEOPLE": "No one met yet. People appear here as you learn about them.",
                              "KEYS": "No passwords or codes yet. Clues that unlock things are filed here."}.get(
                name, "Nothing recorded here yet. Examine objects, read files, and switch frequencies: many clues exist on only one band."),
                99999, x + 16, y + 90, w - 32, DIM, 8)
        else:
            visible = 10
            top = max(0, min(sel - visible + 1, len(items) - visible)) if sel >= visible else 0
            for row, (label, _) in enumerate(items[top:top + visible]):
                i = top + row
                yy = y + 86 + row * 15
                on = i == sel
                if on:
                    p.fillRect(x + 8, yy - 10, 152, 14, QColor(50, 90, 120, 160))
                ui.text(p, elide(label, 144, 7), x + 12, yy, AMBER if on else TEXT, 7)
            p.fillRect(x + 166, y + 74, 1, h - 96, QColor(60, 90, 110))
            data = items[sel][1]
            if name == "STORY":
                self._story(p, data, x, y, w)
            elif name == "PUZZLES":
                fl, title, hint, reward = next(pz for pz in PUZZLES if pz[0] == data)
                done = fl in gp.flags
                ui.text(p, title, x + 176, y + 88, GREEN if done else AMBER, 9, True, glow=True)
                ui.text(p, "COMPLETE" if done else "IN PROGRESS", x + 176, y + 100, GREEN if done else DIM, 7, True)
                yy = ui.type_lines(p, hint, 99999, x + 176, y + 118, w - 196, TEXT, 8, 11)
                if done:
                    ui.text(p, "REWARD", x + 176, yy + 8, GREEN, 7, True)
                    ui.type_lines(p, reward, 99999, x + 176, yy + 20, w - 196, QColor(170, 255, 200), 8, 11)
            elif name == "TAPES":
                band = int(data["cat"])
                c = QColor(*TINT[band])
                ui.text(p, data["title"], x + 176, y + 88, c, 9, True, glow=True)
                ui.text(p, f"{FREQS[band]} MHz  {FREQ_NAMES[band]}", x + 176, y + 100, DIM, 7)
                ui.type_lines(p, '"' + data["text"] + '"', 99999, x + 176, y + 118, w - 196, TEXT, 8, 11)
            else:
                ui.text(p, data["title"], x + 176, y + 88, AMBER, 9, True, glow=True)
                ui.type_lines(p, data["text"], 99999, x + 176, y + 106, w - 196, TEXT, 8, 11)
        ui.text(p, "A/D tab   W/S select   J or ESC close", x + 12, y + h - 8, DIM, 7)
        p.restore()

    def _story(self, p, ch, x, y, w):
        gp = self.gp
        state = self.chapter_state(ch)
        if state == "locked":
            ui.text(p, "CHAPTER " + str(ch.n), x + 176, y + 88, DIM, 9, True)
            ui.type_lines(p, "Not reached yet.", 99999, x + 176, y + 106, w - 196, DIM, 8)
            return
        ui.text(p, f"CHAPTER {ch.n}: {ch.title}", x + 176, y + 88, GREEN if state == "done" else AMBER, 9, True, glow=True)
        yy = y + 102
        for m in ch.missions:
            done = "m_" + m.id in gp.flags
            current = not done and all(("m_" + q.id) in gp.flags for q in ch.missions[:ch.missions.index(m)])
            ui.text(p, ("[x] " if done else "[>] " if current else "[ ] ") + m.text, x + 176, yy,
                    GREEN if done else AMBER if current else DIM, 7, current)
            yy += 11
        ui.type_lines(p, ch.recap if state == "done" else ch.hook, 99999, x + 176, yy + 6, w - 196, TEXT, 7, 10)
