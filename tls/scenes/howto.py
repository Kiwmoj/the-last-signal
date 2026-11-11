"""How to Play: five cards, big keycaps, tiny icons. Readable in about 20 seconds.

Opened from the main menu (button starts the game) or from the pause menu (button resumes).
Navigation: A/D or arrows pick a button, ENTER/E/SPACE press it, ESC goes back. Buttons also react to the mouse.
"""
import math
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPen, QPolygonF

from ..constants import W, H, CYAN, AMBER, TEXT, DIM, GREEN
from ..engine import Scene
from ..echo import draw_device
from ..world import TINT
from .. import ui
from .menu import draw_backdrop

ROWS = [
    ("MOVE", "Explore the abandoned station.", (80, 230, 255)),
    ("INTERACT", "Interact with radios, computers, doors and objects.", (255, 176, 60)),
    ("CHANGE FREQUENCY", "Switch between 88.1, 104.7 and 121.3 MHz to discover hidden things.", (190, 90, 255)),
    ("ECHO RECEIVER", "Detect mysterious signals and find clues.", (90, 255, 150)),
    ("SOLVE THE MYSTERY", "Explore, collect clues, solve puzzles and discover the truth.", (255, 120, 120)),
]
ROW_Y0, ROW_H = 40, 36


# ---------------------------------------------------------------- little drawing helpers
def keycap(p, x, y, label, w=14, h=14, lit=0.0, arrow=None):
    """A keyboard key: bevelled cap, optional glow when 'pressed', letter or arrow glyph."""
    off = 1 if lit > .6 else 0
    p.fillRect(x, y + 2, w, h, QColor(14, 16, 24))                       # shadow / key side
    p.fillRect(x, y + off, w, h - 1, QColor(58, 66, 86) if lit < .6 else QColor(90, 80, 50))
    p.fillRect(x, y + off, w, 1, QColor(150, 160, 190))
    p.fillRect(x + 1, y + off + 1, w - 2, h - 4, QColor(40, 46, 62) if lit < .6 else QColor(120, 96, 40))
    if lit > 0:
        p.fillRect(x - 1, y + off - 1, w + 2, h + 1, QColor(255, 200, 90, int(60 * lit)))
    col = AMBER if lit > .3 else TEXT
    if arrow:
        cx, cy = x + w / 2, y + off + (h - 3) / 2
        dx, dy = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}[arrow]
        pts = [QPointF(cx + dx * 3, cy + dy * 3), QPointF(cx - dy * 3 - dx * 2, cy + dx * 3 - dy * 2),
               QPointF(cx + dy * 3 - dx * 2, cy - dx * 3 - dy * 2)]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawPolygon(QPolygonF(pts))
    else:
        ui.text(p, label, x + w / 2, y + off + h - 4, col, 8, True, True)


def icon(p, kind, cx, cy, col, t):
    """16 px icons: move arrows, interact ring, radio waves, handheld receiver, magnifier."""
    c = QColor(*col)
    p.save()
    p.translate(cx, cy)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(c, 1))
    if kind == 0:                                              # four arrows
        for ang in range(0, 360, 90):
            p.save(); p.rotate(ang)
            p.setBrush(c); p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(QPolygonF([QPointF(0, -8), QPointF(-3, -4), QPointF(3, -4)]))
            p.restore()
        p.setPen(QPen(c, 1)); p.drawEllipse(QPointF(0, 0), 2, 2)
    elif kind == 1:                                            # pulsing ring + hand dot
        r = 4 + 3 * (.5 + .5 * math.sin(t * 4))
        p.drawEllipse(QPointF(0, 0), r + 2, r + 2)
        p.setBrush(c); p.drawEllipse(QPointF(0, 0), 3, 3)
    elif kind == 2:                                            # animated wave
        prev = None
        for i in range(-8, 9):
            y = math.sin(i * .6 + t * 6) * 4
            if prev is not None:
                p.drawLine(QPointF(i - 1, prev), QPointF(i, y))
            prev = y
        p.drawRect(QRectF(-9, -7, 18, 14))
    elif kind == 3:                                            # the Echo Receiver handheld
        draw_device(p, -7, -10, .32, t, 1, .6, 0)
    else:                                                      # magnifier with a question mark
        p.drawEllipse(QPointF(-1, -1), 5, 5)
        p.setPen(QPen(c, 2)); p.drawLine(QPointF(3, 3), QPointF(7, 7))
        ui.text(p, "?", -1, 2, c, 7, True, True)
    p.restore()


class HowToScene(Scene):
    def __init__(self, game, from_pause=False):
        super().__init__(game)
        self.from_pause = from_pause
        self.t = 0.0
        self.sel = 0
        self.buttons = [
            ("RESUME GAME" if from_pause else "PLAY GAME", QRectF(110, 232, 180, 24)),
            ("BACK", QRectF(300, 232, 90, 24)),
        ]

    # ------------------------------------------------------------------ navigation
    def update(self, dt):
        self.t += dt
        self.game.audio.set_music(.7)

    def activate(self, i):
        self.game.audio.play("click")
        if i == 0:
            self.primary()
        else:
            self.game.pop()

    def primary(self):
        if self.from_pause:
            self.game.pop()          # leave How to Play
            self.game.pop()          # leave the pause menu -> back in the game
            return
        from .gameplay import GameplayScene
        from .intro import IntroScene
        if self.game.save.data.get("progress"):
            self.game.replace(GameplayScene(self.game, load=True))
        else:
            self.game.replace(IntroScene(self.game))

    def key_press(self, k):
        K = Qt.Key
        if k == K.Key_Escape:
            self.game.audio.play("click")
            self.game.pop()
        elif k in (K.Key_A, K.Key_Left, K.Key_D, K.Key_Right, K.Key_Tab):
            self.sel = (self.sel + 1) % 2
            self.game.audio.play("click", .4)
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E, K.Key_Space):
            self.activate(self.sel)

    def _hit(self, x, y):
        for i, (_, r) in enumerate(self.buttons):
            if r.contains(x, y):
                return i
        return None

    def mouse_move(self, x, y):
        i = self._hit(x, y)
        if i is not None:
            self.sel = i

    def mouse_press(self, x, y):
        i = self._hit(x, y)
        if i is not None:
            self.sel = i
            self.activate(i)

    # ------------------------------------------------------------------ drawing
    def draw(self, p):
        t = self.t
        draw_backdrop(p, t)
        p.fillRect(0, 0, W, H, QColor(2, 4, 10, 196))
        ui.text_spaced(p, "HOW TO PLAY", W / 2, 28, CYAN, 15, 4, True, True)
        p.fillRect(150, 34, 180, 1, QColor(80, 230, 255, 90))
        active = int(t / 1.5) % 5            # the row whose keys are being "pressed"
        pulse = .5 + .5 * math.sin(t * 7)
        for i, (title, desc, col) in enumerate(ROWS):
            y = ROW_Y0 + i * ROW_H
            on = i == active
            c = QColor(*col)
            p.fillRect(18, y, 444, ROW_H - 3, QColor(10, 16, 28, 230))
            p.fillRect(18, y, 3, ROW_H - 3, c)
            if on:
                p.fillRect(18, y, 444, ROW_H - 3, QColor(c.red(), c.green(), c.blue(), 18))
            ui.text(p, str(i + 1), 31, y + 21, QColor(c.red(), c.green(), c.blue(), 200), 14, True, True)
            icon(p, i, 58, y + 16, col, t)
            ui.text(p, title, 80, y + 12, c, 9, True, glow=on)
            lines = ui.wrap(desc, 215, 7)
            for j, ln in enumerate(lines[:2]):
                ui.text(p, ln, 80, y + 22 + j * 8, TEXT, 7)
            self._keys(p, i, y, on, pulse)
        # buttons
        for i, (label, r) in enumerate(self.buttons):
            primary = i == 0
            hot = i == self.sel
            base = QColor(30, 100, 60) if primary else QColor(24, 32, 48)
            edge = GREEN if primary else CYAN
            if hot:
                glow = int(40 + 30 * math.sin(t * 6))
                p.fillRect(QRectF(r.x() - 2, r.y() - 2, r.width() + 4, r.height() + 4), QColor(edge.red(), edge.green(), edge.blue(), glow))
            p.fillRect(r, base if not hot else base.lighter(130))
            p.setPen(QPen(edge if hot else DIM, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(r.x() + .5, r.y() + .5, r.width() - 1, r.height() - 1))
            ui.text(p, ("> " + label + " <") if hot else label, r.center().x(), r.y() + 16,
                    (QColor(255, 255, 255) if hot else TEXT), 10 if primary else 8, True, True, hot)
        ui.text(p, "A / D choose     ENTER select     ESC back", W / 2, H - 5, DIM, 7, False, True)

    def _keys(self, p, i, y, on, pulse):
        lit = pulse if on else 0.0
        ky = y + 9
        if i == 0:                                   # W A S D  /  arrows
            x = 308
            for ch in "WASD":
                keycap(p, x, ky, ch, 14, 14, lit); x += 16
            ui.text(p, "/", x + 1, ky + 11, DIM, 9, True)
            x += 11
            for d in "LDUR":
                keycap(p, x, ky, "", 14, 14, lit, arrow=d); x += 16
        elif i == 1:
            keycap(p, 420, ky, "E", 20, 15, lit)
        elif i == 2:
            keycap(p, 308, ky, "Q", 20, 15, lit)
            x = 336
            for fv, k in (("88.1", 0), ("104.7", 1), ("121.3", 2)):
                c = QColor(*TINT[k])
                wpx = len(fv) * 5 + 6
                p.fillRect(x, ky + 1, wpx, 12, QColor(c.red() // 6, c.green() // 6, c.blue() // 6))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(c); p.drawRect(x, ky + 1, wpx - 1, 11)
                ui.text(p, fv, x + wpx / 2, ky + 10, c, 6, True, True)
                x += wpx + 3
        elif i == 3:
            keycap(p, 420, ky, "R", 20, 15, lit)
        else:
            x = 330
            for label, c in (("CLUES", (255, 176, 60)), ("PUZZLES", (80, 230, 255)), ("TRUTH", (255, 120, 120))):
                ui.text(p, label, x, ky + 10, QColor(*c), 7, True)
                x += len(label) * 5 + 8
                if label != "TRUTH":
                    ui.text(p, ">", x - 4, ky + 10, DIM, 7, True)
                    x += 4
