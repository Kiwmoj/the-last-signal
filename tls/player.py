"""Player: smooth acceleration-based movement, axis-separated AABB collision, procedural sprite."""
import math
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QColor

SPEED = 82.0
ACCEL = 700.0
FEET_W, FEET_H = 8, 4   # collision box is only the feet, which gives the 3/4 depth look


def _approach(v, target, step):
    if v < target:
        return min(v + step, target)
    return max(v - step, target)


def box(p, x, y, w, h, c):
    p.fillRect(int(x), int(y), int(w), int(h), QColor(*c))


class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)   # (x, y) = point between the feet
        self.vx = self.vy = 0.0
        self.facing = "down"
        self.anim = 0.0
        self.moving = False

    def feet(self):
        return QRectF(self.x - FEET_W / 2, self.y - FEET_H, FEET_W, FEET_H)

    def update(self, dt, ix, iy, solids):
        n = math.hypot(ix, iy)
        if n:
            ix, iy = ix / n, iy / n
            if abs(ix) >= abs(iy):
                self.facing = "right" if ix > 0 else "left"
            else:
                self.facing = "down" if iy > 0 else "up"
        # Accelerate toward the target velocity so movement feels smooth, not snappy.
        self.vx = _approach(self.vx, ix * SPEED, ACCEL * dt)
        self.vy = _approach(self.vy, iy * SPEED, ACCEL * dt)
        self.x += self.vx * dt
        self._resolve(solids, True)
        self.y += self.vy * dt
        self._resolve(solids, False)
        self.moving = math.hypot(self.vx, self.vy) > 10
        if self.moving:
            self.anim += dt

    def _resolve(self, solids, horizontal):
        f = self.feet()
        for s in solids:
            if f.intersects(s):
                if horizontal:
                    self.x = s.left() - FEET_W / 2 if self.vx > 0 else s.right() + FEET_W / 2
                    self.vx = 0
                else:
                    self.y = s.top() if self.vy > 0 else s.bottom() + FEET_H
                    self.vy = 0
                f = self.feet()

    def draw(self, p, t):
        x, y = int(round(self.x)), int(round(self.y))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawEllipse(QPointF(x, y - 1), 7, 3)
        step = math.sin(self.anim * 12) if self.moving else 0.0
        bob = 1 if (self.moving and abs(step) > .6) else 0
        f = self.facing
        side = f in ("left", "right")
        # legs + boots
        lh = 6 - (1 if step > .3 else 0)
        rh = 6 - (1 if step < -.3 else 0)
        if side:
            box(p, x - 3, y - lh, 3, lh, (30, 34, 46)); box(p, x, y - rh, 3, rh, (30, 34, 46))
            box(p, x - 3, y - 2, 3, 2, (20, 20, 26)); box(p, x, y - 2, 3, 2, (20, 20, 26))
        else:
            box(p, x - 4, y - lh, 3, lh, (30, 34, 46)); box(p, x + 1, y - rh, 3, rh, (30, 34, 46))
            box(p, x - 4, y - 2, 3, 2, (20, 20, 26)); box(p, x + 1, y - 2, 3, 2, (20, 20, 26))
        # coat
        bw = 8 if side else 10
        bx = x - bw // 2
        by = y - 14 - bob
        box(p, bx, by, bw, 9, (44, 92, 110))
        box(p, bx, by, bw, 1, (86, 146, 168))
        box(p, bx, by + 6, bw, 1, (24, 40, 50))
        # arms swing opposite to legs
        sw = int(round(step * 1.5))
        if side:
            box(p, x - 1, by + 1 + sw, 3, 6, (38, 78, 94))
        else:
            box(p, bx - 2, by + 1 + sw, 2, 6, (38, 78, 94))
            box(p, bx + bw, by + 1 - sw, 2, 6, (38, 78, 94))
        # scarf with a flutter tail
        box(p, bx, by - 1, bw, 2, (240, 160, 50))
        if side:
            tx = bx - 2 if f == "right" else bx + bw
            box(p, tx, by, 2, 4 + (1 if bob else 0), (214, 134, 40))
        # head
        hy = y - 22 - bob
        box(p, x - 4, hy, 8, 7, (228, 186, 152))
        hair = (46, 32, 30)
        if f == "up":
            box(p, x - 4, hy - 1, 8, 8, hair)
        else:
            box(p, x - 4, hy - 1, 8, 3, hair)
            if f == "left":
                box(p, x + 1, hy, 3, 6, hair)
            elif f == "right":
                box(p, x - 4, hy, 3, 6, hair)
            eye = (18, 20, 30)
            if f == "down":
                box(p, x - 2, hy + 3, 1, 2, eye); box(p, x + 1, hy + 3, 1, 2, eye)
            elif f == "left":
                box(p, x - 3, hy + 3, 1, 2, eye)
            else:
                box(p, x + 2, hy + 3, 1, 2, eye)
        # radio-operator headphones with glowing cups
        box(p, x - 5, hy - 2, 10, 1, (60, 66, 80))
        glow = 150 + int(90 * math.sin(t * 4))
        cup = (70, 76, 92)
        if side:
            box(p, x - 1, hy + 1, 3, 4, cup)
            p.fillRect(x, hy + 2, 1, 2, QColor(80, 230, 255, glow))
        else:
            box(p, x - 6, hy + 1, 2, 4, cup); box(p, x + 4, hy + 1, 2, 4, cup)
            p.fillRect(x - 6, hy + 2, 1, 2, QColor(80, 230, 255, glow))
            p.fillRect(x + 5, hy + 2, 1, 2, QColor(80, 230, 255, glow))
