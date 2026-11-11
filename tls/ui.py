"""Small UI drawing helpers (glow text, panels)."""
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QFont, QColor, QPen, QFontMetrics
from .constants import PANEL, DIM


def font(size=8, bold=False):
    f = QFont("Consolas", size)
    f.setBold(bold)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


def text(p, s, x, y, color, size=8, bold=False, center=False, glow=False):
    """Draw text; x is the centre if center=True. y is the baseline."""
    p.setFont(font(size, bold))
    if center:
        x = x - QFontMetrics(p.font()).horizontalAdvance(s) / 2
    if glow:
        g = QColor(color)
        g.setAlpha(60)
        p.setPen(g)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p.drawText(int(x + dx), int(y + dy), s)
    p.setPen(color)
    p.drawText(int(x), int(y), s)


def text_spaced(p, s, cx, y, color, size=10, spacing=3, bold=True, glow=False):
    """Centred, letter-spaced heading text (cinematic titles)."""
    p.setFont(font(size, bold))
    fm = QFontMetrics(p.font())
    total = sum(fm.horizontalAdvance(c) + spacing for c in s) - spacing
    x = cx - total / 2
    for c in s:
        if glow:
            g = QColor(color)
            g.setAlpha(50)
            p.setPen(g)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                p.drawText(int(x + dx), int(y + dy), c)
        p.setPen(color)
        p.drawText(int(x), int(y), c)
        x += fm.horizontalAdvance(c) + spacing


def wrap(s, width_px, size=8):
    """Word-wrap a string to a pixel width using real font metrics."""
    fm = QFontMetrics(font(size))
    lines, cur = [], ""
    for w in s.split():
        trial = (cur + " " + w).strip()
        if fm.horizontalAdvance(trial) > width_px and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def panel(p, x, y, w, h, border=DIM):
    p.fillRect(QRectF(x, y, w, h), PANEL)
    p.setPen(QPen(border, 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(x + .5, y + .5, w - 1, h - 1))


def type_lines(p, full, shown, x, y, width, color, size=8, step=12, glitch=0.0, t=0.0):
    """Draw `full` word-wrapped, revealing only the first `shown` characters (typewriter).
    The whole text is wrapped first so words never jump lines while typing. Returns the next y."""
    count = 0
    for ln in wrap(full, width, size):
        part = ln[:max(0, int(shown) - count)]
        count += len(ln) + 1
        if part:
            if glitch:
                # unsettling recordings: a few characters flicker into symbols
                part = "".join(c if (c == " " or ((hash((i, int(t * 12))) % 100) / 100) > glitch) else "#%&?"[i % 4]
                               for i, c in enumerate(part))
            text(p, part, x, y, color, size)
        y += step
    return y


def scope(p, x, y, w, h, t, color, amp=1.0, noise=0.2, pulses=0):
    """Oscilloscope: a sine trace, or `pulses` spikes per cycle, plus static noise."""
    import math
    import random
    p.fillRect(int(x), int(y), int(w), int(h), QColor(2, 10, 14))
    p.setPen(QColor(color.red(), color.green(), color.blue(), 28))
    for gx in range(0, int(w), 16):
        p.drawLine(int(x + gx), int(y), int(x + gx), int(y + h))
    p.drawLine(int(x), int(y + h / 2), int(x + w), int(y + h / 2))
    p.setPen(QPen(color, 1))
    prev = None
    for i in range(int(w)):
        u = i / w
        if pulses:
            ph = (u * pulses * 1.0 + t * .4) % 1.0
            v = math.exp(-((ph - .5) * 14) ** 2) * 1.8 * amp * (1 if int(u * pulses + t * .4) % 2 == 0 else -1)
            v += math.sin(i * .5 + t * 9) * .08
        else:
            v = math.sin(u * 22 + t * 8) * math.sin(u * 3 + t) * amp
        v += random.uniform(-1, 1) * noise
        py = y + h / 2 - max(-1, min(1, v)) * (h / 2 - 3)
        if prev is not None:
            p.drawLine(int(x + i - 1), int(prev), int(x + i), int(py))
        prev = py
    p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 120), 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(int(x), int(y), int(w), int(h))


def overlay_open(p, t, dim=170):
    """Shared fade-in for overlay screens. Returns eased 0..1 and dims what is underneath."""
    a = min(1.0, t / .25)
    a = 1 - (1 - a) ** 3
    p.fillRect(0, 0, 480, 270, QColor(0, 0, 8, int(dim * a)))
    p.setOpacity(a)
    p.translate(0, (1 - a) * 10)
    return a


def overlay_close(p):
    p.translate(0, 0)
    p.setOpacity(1.0)
