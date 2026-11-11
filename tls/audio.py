"""Procedural sound effects. WAVs are synthesised once into a temp folder and played with
QSoundEffect (no asset files). Every call is guarded, so a machine without audio just stays silent."""
import math
import os
import random
import struct
import tempfile
import wave

try:
    from PyQt6.QtCore import QUrl
    from PyQt6.QtMultimedia import QSoundEffect
except Exception:          # pragma: no cover - audio is optional
    QSoundEffect = None

RATE = 22050


def _render(fn, dur):
    n = int(RATE * dur)
    return [max(-1.0, min(1.0, fn(i / RATE, i / n))) for i in range(n)]


def _noise(): return random.uniform(-1, 1)


def _sounds():
    sq = lambda f, t: 1.0 if math.sin(2 * math.pi * f * t) > 0 else -1.0
    sine = lambda f, t: math.sin(2 * math.pi * f * t)
    return {
        "blip": _render(lambda t, u: .35 * sq(820 + 60 * math.sin(t * 90), t) * (1 - u) ** 2, .035),
        "click": _render(lambda t, u: .5 * _noise() * (1 - u) ** 3, .05),
        "tune": _render(lambda t, u: (.28 * sine(260 + 900 * u * u, t) + .18 * _noise() * (1 - u)) * math.sin(math.pi * u), .45),
        "static": _render(lambda t, u: .35 * _noise() * math.sin(math.pi * u), .3),
        "ok": _render(lambda t, u: .4 * sine((523, 659, 784, 1046)[min(3, int(u * 4))], t) * (1 - u) ** 1.2, .55),
        "bad": _render(lambda t, u: .4 * sq(110 - 30 * u, t) * (1 - u), .35),
        "pickup": _render(lambda t, u: .4 * sine(500 + 700 * u, t) * (1 - u), .2),
        "door": _render(lambda t, u: (.45 * sine(55 + 25 * math.sin(t * 8), t) + .25 * _noise()) * math.sin(math.pi * u), .9),
        "note": _render(lambda t, u: .3 * sine(880, t) * (1 - u) ** 2, .12),
        "hum": _render(lambda t, u: .22 * _noise() * .6 + .12 * sine(60, t) + .08 * sine(120, t), 1.0),
        "alert": _render(lambda t, u: .38 * sq((880, 0, 660, 0, 880)[min(4, int(u * 5))] or 1, t) * (1.0 if int(u * 5) % 2 == 0 else 0.0), .6),
        "thud": _render(lambda t, u: .7 * sine(52 - 20 * u, t) * (1 - u) ** 2 + .25 * _noise() * (1 - u) ** 6, .7),
        "crackle": _render(lambda t, u: (_noise() * (1.0 if random.random() < .05 else 0.0)) * .6, .35),
        "rise": _render(lambda t, u: (.25 * sine(120 + 700 * u * u, t) + .15 * _noise()) * u, 1.4),
        "scan": _render(lambda t, u: .3 * sine(300 + 1500 * (1 - abs(2 * u - 1)), t) * math.sin(math.pi * u), .5),
    }


NAMES = ("blip", "click", "tune", "static", "ok", "bad", "pickup", "door", "note", "hum", "alert", "thud", "crackle", "rise", "scan")

# ---- background music -------------------------------------------------------------------------------------
# Moods: menu / control (Control Room) / explore / unknown (121.3 MHz) / revelation (story discoveries, the chamber)
# / chapter (one-shot stinger). They are synthesised by tls/musicgen.py in a separate process the first time the game
# runs. To use your own music instead, drop WAV files named after a mood into the project's  music/  folder
# (for example music/menu.wav). A WAV in that folder always wins over the generated one.
MOODS = ("menu", "control", "explore", "unknown", "revelation", "chapter")
MOOD_GAIN = {"menu": .55, "control": .5, "explore": .55, "unknown": .55, "revelation": .65, "chapter": .7}
FADE_IN, FADE_OUT = .30, .45        # volume units per second: a track takes about a second to fade out, then the next fades in
MUSIC_CACHE = os.path.join(tempfile.gettempdir(), "the_last_signal_music_v1")
MUSIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "music")


class Audio:
    def __init__(self, settings):
        self.settings = settings
        self.fx = {}
        self.loop = None
        self.tracks = {}                          # mood -> QSoundEffect, created lazily, one per mood
        self.vol = {m: 0.0 for m in MOODS}        # current (faded) volume of each track
        self.mood = None
        self.level = 0.0                          # scene-requested music level 0..1 (multiplied by the Music slider)
        self.paused = False
        self._stinger_done = False
        self._probe = 0.0
        if QSoundEffect is None:
            return
        try:
            folder = os.path.join(tempfile.gettempdir(), "the_last_signal_audio_v2")
            os.makedirs(folder, exist_ok=True)
            cached = all(os.path.exists(os.path.join(folder, n + ".wav")) for n in NAMES)
            sounds = {} if cached else _sounds()      # synthesised once, then reused from the cache folder
            for name in NAMES:
                path = os.path.join(folder, name + ".wav")
                if not cached:
                    with wave.open(path, "wb") as w:
                        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
                        w.writeframes(b"".join(struct.pack("<h", int(s * 32000)) for s in sounds[name]))
                e = QSoundEffect()
                e.setSource(QUrl.fromLocalFile(path))
                self.fx[name] = e
            if "hum" in self.fx:
                self.loop = self.fx["hum"]
                self.loop.setLoopCount(-2)      # QSoundEffect.Infinite
                self.loop.setVolume(0.0)
        except Exception:
            self.fx = {}
            self.loop = None
        self._start_music_generator()

    # ---- music generation / loading ----
    def _start_music_generator(self):
        """Synthesise the soundtrack in a background process (the first run only) so the game never stalls."""
        try:
            if all(os.path.exists(os.path.join(MUSIC_CACHE, m + ".wav")) for m in MOODS):
                return
            import subprocess
            import sys
            flags = 0x08000000 if os.name == "nt" else 0         # CREATE_NO_WINDOW
            subprocess.Popen([sys.executable, "-m", "tls.musicgen", MUSIC_CACHE], cwd=os.path.dirname(MUSIC_DIR),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        except Exception:
            pass

    def _track(self, mood):
        """The QSoundEffect for a mood, loaded on first use (None while the file does not exist yet)."""
        e = self.tracks.get(mood)
        if e is not None or QSoundEffect is None:
            return e
        for path in (os.path.join(MUSIC_DIR, mood + ".wav"), os.path.join(MUSIC_CACHE, mood + ".wav")):
            if os.path.exists(path):
                try:
                    e = QSoundEffect()
                    e.setSource(QUrl.fromLocalFile(path))
                    e.setLoopCount(1 if mood == "chapter" else -2)
                    e.setVolume(0.0)
                    self.tracks[mood] = e
                    return e
                except Exception:
                    return None
        return None

    def _sfx_vol(self):
        return max(0, min(10, self.settings.get("sfx_volume", 7))) / 10.0

    _vol = _sfx_vol

    def _music_vol(self):
        return max(0, min(10, self.settings.get("music_volume", 6))) / 10.0

    def set_mood(self, mood):
        """Choose which soundtrack plays. Cheap to call every frame; only a change starts a fade."""
        if mood != self.mood:
            self.mood = mood
            self._stinger_done = False

    def set_music(self, level):
        """Overall music level 0..1 requested by the current scene (0 fades the music out)."""
        self.level = max(0.0, min(1.0, level))

    def set_paused(self, paused):
        self.paused = paused

    def tick(self, dt):
        """Advance the music fades. Called once per frame by the game loop. Tracks fade OUT first and the new one fades
        IN afterwards, so two background tracks never overlap."""
        if QSoundEffect is None:
            return
        active = self.mood
        base = self.level * self._music_vol() * (0.0 if self.paused else 1.0)
        others_audible = any(v > .002 for m, v in self.vol.items() if m != active)
        if active and self._probe <= 0 and active not in self.tracks:
            check_files = True
            self._probe = 1.0                     # while a track is still being generated, look for it once a second
        else:
            check_files = False
        self._probe -= dt
        for m in MOODS:
            cur = self.vol[m]
            want = base * MOOD_GAIN[m] if (m == active and not others_audible) else 0.0
            if cur == 0.0 and want == 0.0:
                continue
            e = self.tracks.get(m) or (self._track(m) if check_files and m == active else None)
            if e is None:
                self.vol[m] = 0.0
                continue
            rate = FADE_OUT * (3.0 if self.paused else 1.0) if want < cur else (.8 if m == "chapter" else FADE_IN)
            new = min(want, cur + rate * dt) if want > cur else max(want, cur - rate * dt)
            self.vol[m] = new
            try:
                if new > .002:
                    e.setVolume(new)
                    if not e.isPlaying():
                        if m == "chapter":
                            if not self._stinger_done:
                                self._stinger_done = True
                                e.play()
                        else:
                            e.play()
                elif e.isPlaying():
                    e.stop()
                    self.vol[m] = 0.0
            except Exception:
                pass

    def shutdown(self):
        for e in self.tracks.values():
            try:
                e.stop()
            except Exception:
                pass
        self.set_hum(0)

    def play(self, name, gain=1.0):
        e = self.fx.get(name)
        if e is None:
            return
        try:
            e.setVolume(max(0.0, min(1.0, self._vol() * gain)))
            e.play()
        except Exception:
            pass

    def set_hum(self, level):
        """Background radio static: level 0..1 (0 stops it)."""
        e = self.loop
        if e is None:
            return
        try:
            v = max(0.0, min(1.0, level)) * self._vol() * .35
            e.setVolume(v)
            if v > 0.001 and not e.isPlaying():
                e.play()
            elif v <= 0.001 and e.isPlaying():
                e.stop()
        except Exception:
            pass
