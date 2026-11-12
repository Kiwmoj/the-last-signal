"""Game window, QTimer game loop and scene stack.

The game renders into a small QImage (W x H) with QPainter, then scales it
to the window with nearest-neighbour filtering for a crisp pixel-art look.
The loop is a QTimer, so the UI thread is never blocked.
"""
import os
import time
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QImage, QPainter, QColor
from PyQt6.QtWidgets import QWidget

from .constants import W, H, FPS, BG
from .save import SaveData
from .keymap import Keymap
from .gamepad import Gamepad
from .audio import Audio


class Scene:
    """Base class: scenes get update/draw/key events and a ref to the game."""
    def __init__(self, game):
        self.game = game

    def update(self, dt): pass
    def draw(self, p): pass
    def key_press(self, key): pass
    def key_release(self, key): pass


class GameWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("THE LAST SIGNAL")
        self.resize(W * 3, H * 3)
        self.setMinimumSize(W * 2, H * 2)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.save = SaveData()
        self.keymap = Keymap(self.save.settings)
        self.pad = Gamepad(self)
        self.audio = Audio(self.save.settings)
        self.buffer = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
        self.keys = set()
        self.hide_hud = False
        self._last_scene = None
        self.scene_fade = 0.0
        self.last_screenshot = None
        self.time = 0.0
        self.scenes = []

        from .scenes.menu import MenuScene
        self.push(MenuScene(self))
        if self.save.settings["fullscreen"]:
            self.showFullScreen()

        self._last = time.perf_counter()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000 // FPS)

    # ---- scene stack ----
    def push(self, scene): self.scenes.append(scene)

    def pop(self):
        if len(self.scenes) > 1:
            self.scenes.pop()

    def replace(self, scene):
        self.scenes[-1:] = [scene]

    def set_fullscreen(self, on):
        self.save.settings["fullscreen"] = on
        self.showFullScreen() if on else self.showNormal()

    # ---- loop ----
    def tick(self):
        now = time.perf_counter()
        dt = min(now - self._last, 0.05)
        self._last = now
        self.time += dt
        top = self.scenes[-1]
        if top is not self._last_scene:                     # a different screen: brief fade up from black
            self._last_scene = top
            if not getattr(top, "overlay", False) and type(top).__name__ not in ("GameplayScene", "IntroScene", "EndingScene", "ChapterScene"):
                self.scene_fade = 1.0
        self.scene_fade = max(0.0, self.scene_fade - dt / .28)
        try:
            self.pad.poll(dt)
            top = self.scenes[-1]
            top.update(dt)
        except Exception:
            self._recover(top)
        # music is muted (not restarted) while the pause menu is up, and resumes in place
        self.audio.set_paused(any(getattr(s, "pauses_music", False) for s in self.scenes)
                              and not getattr(self.scenes[-1], "previews_music", False))
        self.audio.tick(dt)
        self.update()

    def _recover(self, scene):
        """A scene raised an error. PyQt would abort the whole process on an uncaught exception inside a timer slot,
        which looks like the window closing by itself. Log it and close the broken overlay instead."""
        import traceback
        try:
            with open(os.path.join(os.path.expanduser("~"), ".the_last_signal_crash.log"), "a", encoding="utf-8") as f:
                f.write(traceback.format_exc() + "\n")
        except OSError:
            pass
        if len(self.scenes) > 1 and getattr(scene, "overlay", False) and self.scenes[-1] is scene:
            self.scenes.pop()

    def paintEvent(self, _):
        bp = QPainter(self.buffer)
        bp.fillRect(0, 0, W, H, BG)
        # Draw from the lowest non-overlay scene so overlays (pause) show what is beneath.
        start = len(self.scenes) - 1
        while start > 0 and getattr(self.scenes[start], "overlay", False):
            start -= 1
        for s in self.scenes[start:]:
            try:
                s.draw(bp)
            except Exception:
                self._recover(s)
                break
        if self.scene_fade > 0:
            bp.fillRect(0, 0, W, H, QColor(0, 0, 0, int(255 * min(1.0, self.scene_fade))))
        if self.save.settings["scanlines"]:
            bp.setPen(QColor(0, 0, 0, 40))
            for y in range(0, H, 2):
                bp.drawLine(0, y, W, y)
        bp.end()

        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0))
        scale = min(self.width() / W, self.height() / H)
        w, h = W * scale, H * scale
        target = QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)
        p.drawImage(target, self.buffer)  # no smoothing hint = pixelated
        p.end()

    # ---- mouse: scenes may define mouse_move(x, y) / mouse_press(x, y) in 480x270 game coordinates ----
    def _to_game(self, pos):
        scale = min(self.width() / W, self.height() / H)
        ox, oy = (self.width() - W * scale) / 2, (self.height() - H * scale) / 2
        return (pos.x() - ox) / scale, (pos.y() - oy) / scale

    def mouseMoveEvent(self, e):
        s = self.scenes[-1]
        if hasattr(s, "mouse_move"):
            s.mouse_move(*self._to_game(e.position()))

    def mousePressEvent(self, e):
        s = self.scenes[-1]
        if e.button() == Qt.MouseButton.LeftButton and hasattr(s, "mouse_press"):
            s.mouse_press(*self._to_game(e.position()))

    def screenshot(self):
        """F12: save the current frame (480x270, scaled up 3x) to a screenshots folder next to the game."""
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
        try:
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, time.strftime("the_last_signal_%Y%m%d_%H%M%S.png"))
            self.buffer.scaled(W * 3, H * 3, Qt.AspectRatioMode.KeepAspectRatio).save(path)
            self.last_screenshot = path
            self.audio.play("click")
        except Exception:
            pass

    # ---- input ----
    def keyPressEvent(self, e):
        if e.isAutoRepeat():
            return
        k = e.key()
        if k == Qt.Key.Key_F11:
            self.set_fullscreen(not self.isFullScreen())
            return
        if k == Qt.Key.Key_F10:                  # screenshot mode: hide the HUD for clean frames
            self.hide_hud = not self.hide_hud
            return
        if k == Qt.Key.Key_F12:
            self.screenshot()
            return
        self.key_down(k)

    def key_down(self, k):
        """A key (or gamepad button) went down."""
        self.keys.add(k)
        self.scenes[-1].key_press(k)

    def key_up(self, k):
        self.keys.discard(k)
        self.scenes[-1].key_release(k)

    def keyReleaseEvent(self, e):
        if e.isAutoRepeat():
            return
        self.key_up(e.key())

    def closeEvent(self, e):
        # Closing the window must never lose progress: save any running game first.
        for s in self.scenes:
            if hasattr(s, "save_progress"):
                s.save_progress()
        self.audio.shutdown()
        self.save.save()
        super().closeEvent(e)
