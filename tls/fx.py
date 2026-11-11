"""Lightweight particle system. 'glow' particles are drawn additively after lighting."""
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPainter


class ParticleSystem:
    MAX = 500

    def __init__(self):
        self.ps = []

    def emit(self, x, y, vx, vy, life, color, size=1, gravity=0.0, glow=False, drag=0.0):
        if len(self.ps) < self.MAX:
            self.ps.append([x, y, vx, vy, life, life, color, size, gravity, glow, drag])

    def update(self, dt):
        alive = []
        for q in self.ps:
            q[4] -= dt
            if q[4] <= 0:
                continue
            q[3] += q[8] * dt
            if q[10]:
                k = max(0.0, 1 - q[10] * dt)
                q[2] *= k
                q[3] *= k
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            alive.append(q)
        self.ps = alive

    def draw(self, p, glow):
        p.setPen(Qt.PenStyle.NoPen)
        for q in self.ps:
            if q[9] != glow:
                continue
            c = QColor(q[6])
            c.setAlpha(int(c.alpha() * q[4] / q[5]))
            p.setBrush(c)
            s = q[7]
            p.drawRect(int(q[0]), int(q[1]), s, s)
