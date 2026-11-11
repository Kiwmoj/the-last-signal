"""The Echo Receiver: pixel-art drawing of the handheld device (used by the pickup banner and the
receiver interface) plus small helpers. Everything is drawn from integer rectangles in a 44 x 70 unit
space so it stays crisp at integer scales."""
import math
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPen

from .world import TINT


def _r(p, x, y, w, h, c):
    p.fillRect(int(x), int(y), int(w), int(h), QColor(*c) if isinstance(c, tuple) else c)


def draw_device(p, x, y, s, t, band=0, strength=0.0, mode=0, dial=None):
    """Draw the Echo Receiver with its top-left at (x, y), scaled by s.
    mode 0/1/2 = SCAN / TRACK / MEMORY: that physical button is pressed in and lit."""
    tint = TINT[band]
    p.save()
    p.translate(x, y)
    p.scale(s, s)
    # antenna with a pulsing tip
    p.setPen(QPen(QColor(150, 156, 168), 1))
    p.drawLine(34, 9, 40, -6)
    glow = 120 + int(120 * (.5 + .5 * math.sin(t * 6)))
    _r(p, 39, -8, 3, 3, (tint[0], tint[1], tint[2], glow))
    # body
    _r(p, 1, 9, 42, 60, (30, 34, 40))            # shadow edge
    _r(p, 0, 8, 42, 60, (74, 82, 70))            # olive casing
    _r(p, 0, 8, 42, 2, (122, 134, 112)); _r(p, 0, 8, 2, 60, (104, 116, 96))
    _r(p, 40, 8, 2, 60, (44, 50, 42)); _r(p, 0, 66, 42, 2, (44, 50, 42))
    for sx, sy in ((3, 11), (37, 11), (3, 63), (37, 63)):
        _r(p, sx, sy, 2, 2, (40, 44, 40))        # screws
    # speaker grille
    for i in range(5):
        _r(p, 6 + i * 4, 11, 2, 3, (34, 38, 34))
    # label strip
    _r(p, 26, 11, 12, 4, (196, 168, 70)); _r(p, 27, 12, 10, 2, (110, 88, 30))
    # display: bezel, glow, animated waveform
    _r(p, 4, 17, 34, 22, (22, 26, 24))
    _r(p, 5, 18, 32, 20, (3, 12, 14))
    _r(p, 5, 18, 32, 20, (tint[0] // 10, tint[1] // 10, tint[2] // 10, 255))
    p.setPen(QPen(QColor(tint[0], tint[1], tint[2]), 1))
    prev = None
    for i in range(32):
        amp = 2 + 6 * (0.25 + strength)
        v = math.sin(i * .6 + t * 9) * math.sin(i * .17 + t * 2) * amp
        if band == 2:
            v += math.sin(i * 2.3 + t * 21) * 1.5
        py = 28 + max(-8, min(8, v))
        if prev is not None:
            p.drawLine(5 + i - 1, int(prev), 5 + i, int(py))
        prev = py
    _r(p, 5, 18, 32, 1, (tint[0], tint[1], tint[2], 90)); _r(p, 5, 37, 32, 1, (tint[0], tint[1], tint[2], 90))
    _r(p, 5, 18 + int((t * 14) % 20), 32, 1, (tint[0], tint[1], tint[2], 60))        # scan line
    # frequency dial: ticks + needle
    _r(p, 4, 42, 20, 20, (46, 52, 44))
    p.setPen(QPen(QColor(24, 28, 24), 1)); p.setBrush(QColor(60, 66, 58))
    p.drawEllipse(QPointF(14, 52), 8, 8)
    p.setPen(QPen(QColor(160, 170, 150), 1))
    for k in range(9):
        a = math.radians(210 - k * 30)
        p.drawLine(QPointF(14 + math.cos(a) * 8.5, 52 - math.sin(a) * 8.5), QPointF(14 + math.cos(a) * 10.5, 52 - math.sin(a) * 10.5))
    frac = ((dial if dial is not None else (88.1, 104.7, 121.3)[band]) - 86) / 38
    a = math.radians(210 - max(0, min(1, frac)) * 240)
    p.setPen(QPen(QColor(tint[0], tint[1], tint[2]), 1))
    p.drawLine(QPointF(14, 52), QPointF(14 + math.cos(a) * 7, 52 - math.sin(a) * 7))
    _r(p, 13, 51, 2, 2, (230, 230, 220))
    # signal-strength LEDs
    lit = int(round(strength * 5))
    for i in range(5):
        on = i < lit
        c = (90, 255, 150) if i < 3 else (255, 176, 60) if i < 4 else (255, 80, 80)
        _r(p, 28 + (i % 2) * 6, 43 + (i // 2) * 5, 4, 3, c if on else (36, 44, 36))
    _r(p, 28, 54, 10, 2, (36, 44, 36))
    # three physical buttons: SCAN (amber), TRACK (cyan), MEMORY (green)
    for i, c in enumerate(((255, 176, 60), (80, 230, 255), (90, 255, 150))):
        bx = 5 + i * 12
        down = 1 if i == mode else 0
        _r(p, bx, 62 + down, 10, 5 - down, (28, 32, 28))
        _r(p, bx + 1, 62 + down, 8, 3, (c[0] // 2, c[1] // 2, c[2] // 2) if not down else c)
        if down:
            _r(p, bx + 3, 63, 4, 1, (255, 255, 255, 160))
    p.restore()
