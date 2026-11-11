"""Exploration gameplay: movement, camera, interaction, radio / frequency system, puzzles, HUD.

FREQUENCY SYSTEM
  radio_on / idx pick the *effective* frequency (`eff`): radio off = 88.1 (the present).
  `self.freq` is the frequency the world currently simulates (collision, visibility, interaction).
  When it changes a transition starts: the old and new worlds are both rendered and the new one is
  revealed through an expanding radio-wave circle, with screen distortion and static on top.

PUZZLES (handlers here, interfaces in scenes/puzzles.py and scenes/terminal.py)
  0. Fuse chain: rubble blocks the corridor on 88.1 -> walk through on 104.7 -> the veil alcove is only
     passable on 121.3 -> take the fuse -> slot it into the transmitter (visible on 104.7).
  1. The Missing Transmission (Old Radio): record three fragments on three frequencies, order them.
  2. Signal lock: once powered, the vault door wants three tones in order: 104.7, 121.3, 88.1.
  3. The Locked Archive (Archive Door): a password assembled from clues on different frequencies.
  4. The Unknown Signal (Transmission Receiver): feed three tones, heaviest pulse count first.
Progress lives in `flags` (+ journal) and is autosaved whenever it changes.
"""
import math
import os
import random
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QImage, QPainter, QRadialGradient, QBrush, QPainterPath, QPen, QPolygonF

from ..constants import W, H, CYAN, AMBER, TEXT, DIM, GREEN
from ..engine import Scene
from ..player import Player
from ..fx import ParticleSystem
from ..journal import Journal
from ..dialogue import Dialog
from ..story import PUZZLES, REWARD, CHAMBER_FILES
from ..chapters import StoryManager, EVENTS, BY_N
from ..tutorial import Tutorial
from ..world import (World, WORLD_W, WORLD_H, ANNEX_END, FREQS, FREQ_NAMES, TINT,
                     draw_prop, draw_windows, draw_beams, lamp_flicker, ceiling_flicker)
from .. import ui

CAM_Y_OFFSET = 18
TRANS_TIME = 0.8
DARK = ((14, 8, 3), (1, 10, 19), (14, 1, 24))   # ambient darkness colour per frequency
TONE_ORDER = [1, 2, 0]                           # 104.7 -> 121.3 -> 88.1
OPEN_FLAG = {"door": "door_open", "secdoor": "archive_open", "chamberdoor": "chamber_open"}   # doors that stop being interactive once open

# People are added to the journal as the player learns about them (clue id -> entries)
PEOPLE = {
    "staff": (("person_elias", "Dr. Elias Marlowe", "Lead researcher of Station 09. Listed as missing since the incident in 1980. Locked the archive and stayed behind."),
              ("person_wren", "Dr. Ada Wren", "Frequency researcher. Believed each band shows a different layer of the same place. Evacuated in 1980.")),
    "belongings": (("person_nora", "Nora Marlowe", "Elias Marlowe's daughter. Nine years old in 1980 and able to hear the unknown band without a headset."),),
    "echo_device": (("person_em", "E.M.", "The initials on the Echo Receiver. Elias Marlowe built it to hear what ordinary radios cannot."),),
}


def _make_vignette():
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    q = QPainter(img)
    g = QRadialGradient(W / 2, H / 2, W * .62)
    g.setColorAt(0.55, QColor(0, 0, 0, 0))
    g.setColorAt(1.0, QColor(0, 0, 0, 170))
    q.fillRect(0, 0, W, H, QBrush(g))
    q.end()
    return img


def _shade(c, f):
    """Push a light colour toward the current frequency's tint."""
    if c is None:
        return None
    k = .3 if f == 0 else .65
    return tuple(int(c[i] * (1 - k) + TINT[f][i] * k) for i in range(3))


def _canvas():
    return QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)


class GameplayScene(Scene):
    def __init__(self, game, load=False, fade_in=False):
        super().__init__(game)
        self.world = World()
        self.player = Player(*self.world.spawn)
        self.lights_on = False
        self.read = set()
        self.minutes = 2 * 60 + 47.0
        # --- progress ---
        self.flags = set()
        self.has_fuse = False
        self.seq = []             # tones entered into the vault lock
        self.heard = set()        # frequencies the beacon has been tuned on
        self.journal = Journal()
        self.memory = Journal()   # recordings stored in the Echo Receiver (cat = band index as text)
        self.frags = set()        # Old Radio fragments recorded (frequency indices)
        self.frozen = False       # True while a puzzle screen is open: world animates, player stands still
        self.tutorial = Tutorial()
        self.fade = 1.0 if fade_in else 0.0      # black overlay fading out after the intro cinematic
        self.item_banner = 0.0                   # "item acquired" banner timer
        self.walked = 0.0
        self._last_pos = None
        # --- story ---
        self.story = StoryManager(self)
        self.events = []                 # story events waiting to play (ids from chapters.EVENTS)
        self.current_event = None
        self.shift = 0.0                 # "reality shift" glitch intensity (Chapter 4 onward)
        self.shift_t = 14.0
        self.mission_toast = 0.0
        self.debug = False                       # F3 overlay, only toggleable when launched with TLS_DEBUG=1
        # --- radio ---
        self.radio_on = False
        self.idx = 0
        self.freq = 0
        self.old_freq = 0
        self.vf = 0               # frequency currently being rendered (read by prop drawers)
        self.trans_t = TRANS_TIME
        self.dial, self.dial_v = FREQS[0], 0.0
        self.signal = 0.0
        self.rings = []
        self.ring_t = 0.0
        self.statics = 0.0
        self.glitch = []

        prog = game.save.data.get("progress") if load else None
        if prog and prog.get("v") != 2:
            prog = None                  # saves from before the story update cannot be resumed
        if prog:
            self.player.x, self.player.y = prog.get("x", self.player.x), prog.get("y", self.player.y)
            self.lights_on = prog.get("lights", False)
            self.read = set(prog.get("read", []))
            self.minutes = prog.get("minutes", self.minutes)
            self.flags = set(prog.get("flags", []))
            self.has_fuse = prog.get("fuse", False)
            self.seq = list(prog.get("seq", []))
            self.heard = set(prog.get("heard", []))
            self.journal = Journal(prog.get("journal", []))
            self.memory = Journal(prog.get("memory", []))
            self.frags = set(prog.get("frags", []))
            self.radio_on = prog.get("radio", False)
            self.idx = prog.get("idx", 0)
            self.freq = self.old_freq = self.eff
            self.dial = FREQS[self.idx] if self.radio_on else FREQS[0]
            self._unstick()

        self.t = 0.0
        self.amb = 150.0 if self.lights_on else 205.0
        self.flash = 0.0
        self.next_flash = random.uniform(5, 10)
        self.spark_t = 1.5
        self.step_t = 0.0
        self.fx = ParticleSystem()
        rnd = random.Random(11)
        self.dust = [[rnd.uniform(0, ANNEX_END), rnd.uniform(70, WORLD_H), rnd.uniform(-4, 4),
                      rnd.uniform(-3, 2), rnd.uniform(0, 6.28)] for _ in range(70)]
        self.dark = _canvas()
        self.cv_old, self.cv_new, self.cv_mix = _canvas(), _canvas(), _canvas()
        self.vignette = _make_vignette()
        self.cam = list(self._cam_target())
        self.dialog = None
        self.focus = None
        self.zone = self.world.zone_name(self.player.x)
        self.banner = 3.5
        self.zone_fade = 1.0                     # 0 -> 1 over 0.7 s after crossing into another room
        self.toast = ""
        self.toast_t = 0.0
        self._sig = self._progress_sig()
        self._sig_t = 0.0
        self._blip = 0

    # ------------------------------------------------------------------ helpers
    @property
    def eff(self):
        """Effective frequency index: 0 (the present) whenever the radio is off."""
        return self.idx if self.radio_on else 0

    @property
    def audio(self):
        return self.game.audio

    def say(self, text, secs=3.5):
        self.toast, self.toast_t = text, secs

    def solids(self):
        return self.world.solids_for(self.freq, self.flags)

    def learn(self, clue):
        """Add a journal entry (tuple from the world/story data). Announces new discoveries."""
        if clue and self.journal.add_tuple(clue):
            self.say("Journal updated  [J]", 3)
            self.audio.play("note")
            for pid, name, text in PEOPLE.get(clue[0], ()):
                self.journal.add(pid, name, text, "person")
            return True
        return False

    def record(self, rid, band, title, text):
        """Store a recording in the Echo Receiver's MEMORY. Returns True if it is new."""
        new = self.memory.add(rid, title, text, str(band))
        if new and "echo_found" in self.flags:
            self.say("Echo Receiver: recording stored", 3)
        return new

    # ---- Echo Receiver detection (shared by the HUD, the SCAN/TRACK screens and the radio meter) ----
    def targets(self, band):
        """World positions of everything still hidden on `band`: clue hotspots and signal sources."""
        out = []
        for h in self.world.hotspots:
            hf, x, y, flag = h[:4]
            need = h[4] if len(h) > 4 else None
            if hf == band and (flag is None or flag not in self.flags) and (need is None or need in self.flags):
                out.append((x, y))
        for pr in self.world.props:
            if pr.action == "source" and band in pr.vis and pr.hide_if not in self.flags \
                    and all(n in self.flags for n in pr.needs if n != "echo_track"):
                c = pr.rect.center()
                out.append((c.x(), c.y()))
        return out

    def nearest(self, band):
        """(distance, dx, dy) to the closest hidden thing on `band`, or None."""
        best = None
        for (x, y) in self.targets(band):
            d = math.hypot(x - self.player.x, y - self.player.y)
            if best is None or d < best[0]:
                best = (d, x - self.player.x, y - self.player.y)
        return best

    def strength(self, band):
        n = self.nearest(band)
        return 0.0 if n is None else max(0.0, min(1.0, 1 - n[0] / 170))

    def complete(self, flag, title, reward):
        """Mark a puzzle flag, log it, and celebrate. No-op if already complete."""
        if flag in self.flags:
            return
        self.flags.add(flag)
        self.journal.add("puzzle_" + flag, title, reward, "puzzle")
        self.flash = 1.0
        self.say(f"Puzzle complete: {title}", 4)
        self.audio.play("ok")
        self.save_progress()

    def _progress_sig(self):
        return (frozenset(self.flags), len(self.journal), len(self.memory), self.has_fuse, tuple(self.seq), frozenset(self.frags))

    def save_progress(self):
        self.game.save.data["progress"] = {
            "x": self.player.x, "y": self.player.y, "lights": self.lights_on,
            "read": sorted(self.read), "minutes": self.minutes, "flags": sorted(self.flags),
            "fuse": self.has_fuse, "seq": self.seq, "heard": sorted(self.heard),
            "radio": self.radio_on, "idx": self.idx, "journal": self.journal.to_list(),
            "memory": self.memory.to_list(), "v": 2,
            "chapter": self.story.chapter().n,
            "frags": sorted(self.frags), "objective": self.objective()}
        self.game.save.save()
        self._sig = self._progress_sig()

    def objective(self):
        """Current mission, e.g. 'CH2  Restore station power' (driven by the story manager)."""
        return self.story.objective_text()

    def hint(self):
        return self.story.hint_text()

    # ------------------------------------------------------------------ story events
    def on_mission_done(self, m):
        self.say("Objective complete: " + m.text, 3)
        self.audio.play("ok")
        self.mission_toast = 2.5

    def on_chapter_done(self, ch):
        self.journal.add(f"chapter_{ch.n}", f"Chapter {ch.n}: {ch.title.title()}", ch.recap, "story")
        self.save_progress()

    def run_events(self):
        """Play the next queued story event when the player is free (not in a menu, dialogue or transition)."""
        if self.current_event or not self.events or self.dialog or self.frozen or self.fade > .3:
            return
        if self.game.scenes[-1] is not self or self.trans_t < .8:
            return
        eid = self.events.pop(0)
        if "evt_" + eid in self.flags:
            return
        self.current_event = eid
        ev = EVENTS[eid]
        self.apply_fx(ev.get("fx"))
        if "card" in ev:
            from .chapter import ChapterScene
            self.game.push(ChapterScene(self.game, self, ev["card"], eid))
        elif ev.get("lines"):
            self.dialog = Dialog("", ev["lines"], "plain", self.freq, on_done=lambda e=eid: self.finish_event(e))
        else:
            self.finish_event(eid)

    def finish_event(self, eid):
        self.flags.add("evt_" + eid)
        self.current_event = None
        if eid == "arrival":
            self.journal.add("person_alex", "Alex Reyes", "You. A young radio technician with the Regional Signals Authority, sent to Station 09 on an emergency assignment in August 1997.", "person")
            self.journal.add("person_dispatch", "Dispatch", "Your contact at the Signals Authority. Reachable by radio. Says Station 09 has been dead since 1980.", "person")
        self.save_progress()

    def apply_fx(self, name):
        if name == "door_lock":
            self.audio.play("door")
            self.flash = .8
        elif name == "flicker":
            self.flash = 1.0
            self.statics = max(self.statics, .5)
            self.audio.play("static", .5)
        elif name == "lights_on":
            self.lights_on = True
            self.flash = 1.0
            self.audio.play("thud", .6)
        elif name == "shift":
            self.shift = 1.0
            self.statics = 1.0
            self.audio.play("static", .8)
            self.glitch = [(random.randint(0, H - 20), random.randint(6, 20), random.uniform(-30, 30)) for _ in range(6)]


    # ------------------------------------------------------------------ input
    def _input(self):
        k, K = self.game.keys, Qt.Key
        ix = (any(a in k for a in (K.Key_D, K.Key_Right))) - (any(a in k for a in (K.Key_A, K.Key_Left)))
        iy = (any(a in k for a in (K.Key_S, K.Key_Down))) - (any(a in k for a in (K.Key_W, K.Key_Up)))
        return ix, iy

    def key_press(self, k):
        K = Qt.Key
        if k == K.Key_Escape:
            self.flags.add("pause_opened")
            from .pause import PauseScene
            self.game.push(PauseScene(self.game, self))
        elif k == K.Key_F3 and os.environ.get("TLS_DEBUG") == "1":
            self.debug = not self.debug
        elif k == K.Key_J and not self.dialog:
            self.flags.add("journal_opened")
            from .journal import JournalScene
            self.game.push(JournalScene(self.game, self))
        elif k == K.Key_R and not self.dialog:
            if "echo_found" not in self.flags:
                self.say("You have nothing to open yet. Look around the room.", 2.5)
            else:
                from .echo_ui import EchoScene
                self.game.push(EchoScene(self.game, self))
        elif k == K.Key_E:
            if self.dialog:
                if self.dialog.advance():
                    d, self.dialog = self.dialog, None
                    if d.on_done:
                        d.on_done()
            elif self.focus:
                self._interact(self.focus)
        elif k == K.Key_Space and not self.dialog:
            self.toggle_radio()
        elif k == K.Key_Q and not self.dialog:
            self.cycle_radio()

    def toggle_radio(self):
        self.radio_on = not self.radio_on
        self.flags.add("radio_used")
        self.audio.play("click")
        if self.radio_on:
            self.say(f"RADIO ONLINE  {FREQS[self.idx]} MHz   [Q] to tune", 3)
            self.ring_t = 0
            self.statics = max(self.statics, .6)
        else:
            self.say("RADIO OFF", 1.5)

    def cycle_radio(self):
        if not self.radio_on:
            self.say("The radio is off. Press SPACE to activate it.", 2.5)
            self.audio.play("bad", .5)
            return
        self.idx = (self.idx + 1) % 3
        self.flags.add("tuned")
        self.audio.play("tune")
        self.say(f"TUNING  {FREQS[self.idx]} MHz  -  {FREQ_NAMES[self.idx]}", 2.5)

    # ------------------------------------------------------------------ frequency switching
    def _begin_transition(self, new):
        self.old_freq, self.freq = self.freq, new
        self.trans_t = 0.0
        self.statics = 1.0
        self.glitch = [(random.randint(0, H - 20), random.randint(6, 20), random.uniform(-30, 30)) for _ in range(6)]
        c = QColor(*TINT[new])
        for _ in range(46):
            a = random.uniform(0, 6.28)
            s = random.uniform(30, 120)
            self.fx.emit(self.player.x, self.player.y - 10, math.cos(a) * s, math.sin(a) * s, random.uniform(.3, .8), c,
                         random.choice((1, 2)), 0, True, 2)
        self._unstick()

    def _unstick(self):
        """If a frequency change leaves the player inside newly solid geometry, move them to the
        nearest free spot."""
        solids = self.solids()
        pl = self.player

        def free():
            fr = pl.feet()
            return not any(fr.intersects(s) for s in solids)

        if free():
            self._safe = (pl.x, pl.y)
            return
        ox, oy = pl.x, pl.y
        sx, sy = getattr(self, "_safe", (None, None))
        if sx is not None:                       # prefer the last spot that was clear: you stay on the side you were on
            pl.x, pl.y = sx, sy
            if free():
                pl.vx = pl.vy = 0
                return
            pl.x, pl.y = ox, oy
        for r in range(2, 140, 2):
            for ang in range(0, 360, 15):
                pl.x, pl.y = ox + math.cos(math.radians(ang)) * r, oy + math.sin(math.radians(ang)) * r
                if free():
                    pl.vx = pl.vy = 0
                    return
        pl.x, pl.y = ox, oy

    REVEAL_EVENTS = ("elias_heard", "c2end", "archive_evt", "c3end", "trail_end", "reveal", "c4end", "purpose_evt", "final_evt")

    def _music_mood(self):
        """Which soundtrack fits what is happening right now."""
        if self.current_event in self.REVEAL_EVENTS or self.zone == "TRANSMISSION CHAMBER":
            return "revelation"
        if self.eff == 2:
            return "unknown"
        return "control" if self.zone == "CONTROL ROOM" else "explore"

    def _bump_hint(self):
        """Tell the player why the collapsed doorway will not let them through (instead of silently blocking)."""
        if "passage_open" in self.flags or self.eff == 1 or self.dialog or self.frozen:
            return
        self._bump_t = getattr(self, "_bump_t", 0.0) - 1 / 60
        if self._bump_t > 0:
            return
        ix = self._input()[0]
        pl = self.player
        if 150 <= pl.y <= 200 and ((ix > 0 and 366 < pl.x < 390) or (ix < 0 and 412 < pl.x < 436)):
            self._bump_t = 4.0
            self.say("The doorway is collapsed. " + ("Tune to 104.7 MHz  [Q]" if self.radio_on else "Radio on [SPACE], then tune to 104.7 MHz  [Q]"), 3.5)
            self.audio.play("bad", .4)

    def _track_safe(self):
        fr = self.player.feet()
        if not any(fr.intersects(s) for s in self.solids()):
            self._safe = (self.player.x, self.player.y)

    def _signal_target(self):
        """Radio signal meter: how close the player is to something hidden on the tuned frequency."""
        return self.strength(self.idx) if self.radio_on else 0.0

    # ------------------------------------------------------------------ interaction
    def _find_focus(self):
        px, py = self.player.x, self.player.y - 2
        best, bd = None, 1e9
        for pr in self.world.props:
            if not (pr.visible(self.freq, self.flags) and pr.interactive_in(self.freq) and pr.zone.contains(px, py)):
                continue
            if OPEN_FLAG.get(pr.action) in self.flags:
                continue
            c = pr.rect.center()
            d = math.hypot(c.x() - px, c.y() - py)
            if pr.action in ("source", "echo_pickup"):
                d -= 1000                    # story-critical pickups win over neighbouring furniture
            if d < bd:
                best, bd = pr, d
        return best

    def _interact(self, pr):
        f, spec = self.freq, pr.spec(self.freq)
        lines = list(spec["lines"])
        style = spec["style"]
        act = pr.action
        self.audio.play("click")
        self.flags.add("tut_interact")
        if act == "echo_pickup":
            self.flags.add("echo_found")
            self.item_banner = 4.0
            self.audio.play("ok")
            self.learn(("echo_device", "The Echo Receiver", "A handheld scanner found in the Control Room. Press R to open it: SCAN finds which band hides something, "
                        "TRACK points the way, MEMORY replays recordings. Hidden signals only appear while it is tracking."))
            self.dialog = Dialog("ECHO RECEIVER", lines, "plain", f)
            return
        if act == "source":
            sid = pr.sid
            self.flags.add("src_" + sid)
            self.flash = .6
            self.audio.play("scan")
            self.record("src_" + sid, f, spec["name"], " ".join(lines[:-1] if sid == "tut" else lines))
            if sid == "tut":
                self.flags.add("tut_signal")
            elif sid == "final":
                self.complete("final_signal", "The Live Voice", REWARD["final_signal"])
            elif sid == "trail3":
                self.complete("trail_done", "Follow the Echoes", REWARD["trail_done"])
        if act == "rack":
            # the Chapter 4 revelation plays as a story event once the flag is set
            self.flags.add("revealed")
            self.flash = 1.0
            self.audio.play("scan")
            self.record("rack09a", 2, "Archive rack 09-A", "A. REYES, August 1997, 03:33 AM: 'Station 09... if anyone can hear this... do not open the archive... it knows you're listening.'")
            self.learn(("rack_09a", "Recording 09-A", "Archive rack 09-A holds a reel labelled A. REYES, August 1997, 03:33 AM: Alex's own voice, speaking the warning that sent Alex here. The unknown signal is Alex."))
            return
        if act == "lights":
            self.lights_on = not self.lights_on
            lines = ["The overhead lights stutter, hum, and wash the room in a sickly glow."] if self.lights_on \
                else ["The lights die. The dark feels thicker than before."]
        elif act == "terminal":
            from .terminal import TerminalScene
            self.game.push(TerminalScene(self.game, self))
            return
        elif act == "terminal2":
            from .terminal import TerminalScene
            self.game.push(TerminalScene(self.game, self, CHAMBER_FILES, "ELIAS MARLOWE  //  RESEARCH TERMINAL"))
            return
        elif act == "oldradio":
            if "beacon" in self.flags:
                from .puzzles import ReconstructScene
                self.game.push(ReconstructScene(self.game, self))
                return
            if "fixed" in self.flags:
                lines = ["The old radio crackles to life, but only static comes out.",
                         "It is tuned to a relay in the research wing, and that relay is not answering yet."]
        elif act == "secdoor":
            from .puzzles import PasswordScene
            self.game.push(PasswordScene(self.game, self))
            return
        elif act == "chamberdoor":
            from .puzzles import PasswordScene, CHAMBER_CFG
            self.game.push(PasswordScene(self.game, self, CHAMBER_CFG))
            return
        elif act == "finaltx":
            from .final import FinalScene, DecisionScene
            self.game.push(DecisionScene(self.game, self) if "final_ready" in self.flags else FinalScene(self.game, self))
            return
        elif act == "receiver":
            from .puzzles import ReceiverScene
            self.game.push(ReceiverScene(self.game, self))
            return
        elif act == "transmitter":
            lines = self._transmitter(f, lines)
        elif act == "door":
            lines = self._door(f, lines)
        elif act == "fuse_take":
            self.has_fuse = True
            self.flags.add("fuse_taken")
            self.say("Picked up: Spare Fuse", 3)
            self.audio.play("pickup")
            self.learn(("fuse", "The spare fuse", "Found a spare fuse in the Unknown. It belongs in the Main Transmitter, which only shows its fuse slot on 104.7."))
            lines.append("It must belong in the transmitter, but the transmitter is on the other side of the rubble.")
        elif act == "beacon":
            lines, style = self._beacon(f, lines), ("voice" if f == 2 else "radio")
        if spec.get("clue"):
            self.learn(spec["clue"])
        self.read.add(spec["name"])
        self.dialog = Dialog(spec["name"].upper(), lines, style, f)

    def open_dialog(self, who, lines, style="plain"):
        self.dialog = Dialog(who, lines, style, self.freq)

    def _transmitter(self, f, lines):
        if "fixed" in self.flags:
            return ["The transmitter hums with borrowed life, restored by a fuse from the Unknown.",
                    "Across the station an old radio and a keypad glow, awake."]
        if f == 1 and self.has_fuse:
            self.has_fuse = False
            self.complete("fixed", "Power the Transmitter", REWARD["fixed"])
            self.lights_on = True
            return ["You slot the spare fuse into slot 3. A thump of current runs through the floor.",
                    "Dials climb. The tubes ignite. The station breathes again, on every frequency.",
                    "The old radio across the room crackles. Somewhere to the east, the research wing door's keypad flickers awake."]
        if f == 0 and self.has_fuse:
            return lines + ["You hold the fuse. Perhaps the radio will show you where it fits."]
        return lines

    def _door(self, f, lines):
        if "fixed" not in self.flags:
            return lines
        self.seq.append(f)
        self.audio.play("click")
        if len(self.seq) < 3:
            return [f"The lock records a tone: {FREQS[f]} MHz  ({len(self.seq)}/3).",
                    "It waits for the rest of the sequence."]
        ok, self.seq = self.seq == TONE_ORDER, []
        if ok:
            self.complete("door_open", "The Signal Lock", REWARD["door_open"])
            self.audio.play("door")
            return ["Memory. The Unknown. The Present. Three tones in the right order.",
                    "The bulkhead shudders, grinds, and slides open. Cold light spills out of a vault beyond."]
        self.audio.play("bad")
        return ["The lock buzzes and resets. Wrong order.",
                "Three clues exist, one on each frequency: one only the past remembers, one the unknown whispers, one the present still shows."]

    def _beacon(self, f, lines):
        self.heard.add(f)
        self.record(f"beacon_{f}", f, f"Experiment Array ({FREQS[f]} MHz)", lines[0])
        self.say(f"Beacon tuned: {len(self.heard)}/3 frequencies", 3)
        if len(self.heard) == 3 and "beacon" not in self.flags:
            self.flags.add("beacon")
            self.flash = 1.0
            self.journal.add("beacon", "The experiment array", "Examined on all three bands. Channel one is the present, channel two replays the past, and channel three, unlabelled, reaches for a moment nobody has lived. "
                                      "Station 09 was not studying radio: it was listening across time.")
            lines += ["Three channels hum together: the present, the past, and a third that belongs to no moment anyone can name.",
                      "Station 09 was not studying radio. It was listening across time. And something started listening back."]
        return lines

    # ------------------------------------------------------------------ update
    def _cam_target(self):
        tx = max(0, min(WORLD_W - W, self.player.x - W / 2))
        ty = max(0, min(WORLD_H - H, self.player.y - CAM_Y_OFFSET - H / 2))
        return tx, ty

    def update(self, dt):
        self.t += dt
        self.minutes += dt / 5
        if self.eff != self.freq:
            self._begin_transition(self.eff)
        self.trans_t = min(TRANS_TIME, self.trans_t + dt)
        self.statics = max(0.0, self.statics - dt * 1.6)

        ix, iy = (0, 0) if (self.dialog or self.frozen) else self._input()
        self.player.update(dt, ix, iy, self.solids())
        self._track_safe()
        if self.dialog and self.dialog.update(dt):
            self.audio.play("blip", .5)
        self.focus = None if (self.dialog or self.frozen) else self._find_focus()
        self.audio.set_hum((.25 + .75 * (1 - self.signal)) * (.5 + .5 * self.statics) if self.radio_on else 0)
        self.audio.set_mood(self._music_mood())
        self.audio.set_music(1.0 if not self.frozen else .7)
        # tutorial bookkeeping
        if self._last_pos is not None:
            self.walked += math.hypot(self.player.x - self._last_pos[0], self.player.y - self._last_pos[1])
            if self.walked > 40:
                self.flags.add("tut_move")
        self._last_pos = (self.player.x, self.player.y)
        self.tutorial.update(self, dt)
        # ---- story ----
        self.story.update()
        self.run_events()
        self.mission_toast = max(0.0, self.mission_toast - dt)
        if self.player.x > 130 and self.zone == "CONTROL ROOM":
            self.flags.add("entered")
        if self.zone == "RESEARCH WING":
            self.flags.add("wing_entered")
        self.shift = max(0.0, self.shift - dt * 1.2)
        if "ch4" in self.flags and "chamber_open" not in self.flags and not self.dialog:
            self.shift_t -= dt                       # the station keeps slipping between versions of itself
            if self.shift_t <= 0:
                self.shift_t = random.uniform(14, 24)
                self.apply_fx("shift")
        # the old radio whispers when you walk past it while it waits to be reconstructed
        if "fixed" in self.flags and "beacon" in self.flags and "p1_done" not in self.flags \
                and math.hypot(self.player.x - 316, self.player.y - 130) < 70 and int(self.t * 1.2) != int((self.t - dt) * 1.2):
            self.audio.play("crackle", .5)
        self.fade = max(0.0, self.fade - dt * .7)
        self.item_banner = max(0.0, self.item_banner - dt)
        self._sig_t += dt
        if self._sig_t > .5:       # autosave whenever progress changed
            self._sig_t = 0.0
            if self._progress_sig() != self._sig:
                self.save_progress()

        # radio dial: a spring, so the needle overshoots and settles like real tuning
        target = FREQS[self.idx] if self.radio_on else FREQS[0]
        self.dial_v += (target - self.dial) * 170 * dt
        self.dial_v *= max(0.0, 1 - 9 * dt)
        self.dial += self.dial_v * dt
        self.signal += (self._signal_target() - self.signal) * min(1.0, dt * 4)
        self.ring_t -= dt
        if self.radio_on and self.ring_t <= 0:
            self.ring_t = 1.7 - 1.1 * self.signal
            self.rings.append([self.player.x, self.player.y - 8, 0.0])
        for r in self.rings:
            r[2] += dt * 60
        self.rings = [r for r in self.rings if r[2] < 110]

        tx, ty = self._cam_target()
        k = min(1.0, dt * 6)
        self.cam[0] += (tx - self.cam[0]) * k
        self.cam[1] += (ty - self.cam[1]) * k

        zone = self.world.zone_name(self.player.x)
        if zone != self.zone:
            self.zone, self.banner = zone, 3.0
            self.zone_fade = 0.0                     # brief dip to black and back when crossing into another room
            self.audio.play("door", .35)
        self.zone_fade = min(1.0, self.zone_fade + dt / .7)
        if self.player.x > 424 and "passage_open" not in self.flags:
            self.flags.add("passage_open")           # you have crossed once: the way back stays open on every frequency
            self.say("The doorway holds. You can come back this way.", 3.5)
        self._bump_hint()
        if zone != "CONTROL ROOM":
            self.flags.add("annex_reached")
        self.banner = max(0.0, self.banner - dt)
        self.toast_t = max(0.0, self.toast_t - dt)
        self._ambient(dt)
        self.fx.update(dt)

    def _ambient(self, dt):
        r = random
        target = 150.0 if self.lights_on else 205.0
        self.amb += (target - self.amb) * min(1.0, dt * 3)
        self.flash = max(0.0, self.flash - dt * 2.2)
        self.next_flash -= dt
        if self.next_flash <= 0:
            self.flash = max(self.flash, .8)
            self.next_flash = r.uniform(7, 16)
        # sparks spit out of the transmitter while it is alive
        self.spark_t -= dt
        if self.spark_t <= 0:
            self.spark_t = r.uniform(1.5, 4.0)
            if self.freq != 0 or "fixed" in self.flags:
                for _ in range(r.randint(3, 7)):
                    self.fx.emit(135 + r.uniform(0, 50), 40, r.uniform(-30, 30), r.uniform(-50, -15), r.uniform(.3, .7),
                                 QColor(*TINT[self.freq]), 1, 140, True)
        if r.random() < dt * (14 if self.freq == 2 else 8):
            self.fx.emit(535 + r.uniform(-8, 8), 172, r.uniform(-4, 4), r.uniform(-22, -10), r.uniform(1, 2),
                         QColor(255, 100, 220, 220), 1, 0, True)
        if self.player.moving:
            self.step_t -= dt
            if self.step_t <= 0:
                self.step_t = .16
                self.fx.emit(self.player.x + r.uniform(-3, 3), self.player.y - 1, r.uniform(-8, 8), r.uniform(-8, -2),
                             .45, QColor(140, 150, 170, 90), 1, 0, False, 2)
        # the Unknown leaks floating motes everywhere
        if self.freq == 2 and r.random() < dt * 10:
            self.fx.emit(self.cam[0] + r.uniform(0, W), self.cam[1] + H, r.uniform(-6, 6), r.uniform(-30, -12),
                         r.uniform(1.5, 3), QColor(200, 110, 255, 200), 1, 0, True)
        for m in self.dust:
            m[4] += dt
            m[0] = (m[0] + (m[2] + math.sin(m[4]) * 3) * dt) % ANNEX_END
            m[1] = 66 + (m[1] - 66 + (m[3] + math.cos(m[4] * .7) * 2) * dt) % (WORLD_H - 66)

    # ------------------------------------------------------------------ lights
    def _lights(self, f):
        """(x, y, radius, brightness, colour) - brightness punches holes in the darkness."""
        t, L, pl = self.t, [], self.player
        fixed = "fixed" in self.flags
        L.append((pl.x, pl.y - 10, 74, .9, None))
        for pr in self.world.props:
            if not pr.visible(f, self.flags):
                continue
            r, cx, k = pr.rect, pr.rect.center().x(), pr.kind
            if k == "console" and (fixed or f != 0):
                L.append((cx, r.bottom() + 6, 90, .55 + .1 * math.sin(t * 5), (60, 200, 255)))
            elif k == "computer":
                L.append((cx, r.y() + 18, 55, .5 if (f or fixed) else .3, (80, 255, 140)))
            elif k == "rack":
                L.append((cx, r.y() + 40, 42, .3, (90, 130, 255)))
            elif k == "table":
                L.append((r.right() - 14, r.y() - 2, 95, .85 * lamp_flicker(t), (255, 170, 70)))
            elif k == "artifact" and f != 1:
                L.append((cx, r.y() + 16, 85, .65 + .15 * math.sin(t * 2), (255, 70, 200)))
            elif k == "door":
                if "door_open" in self.flags:
                    L.append((r.right() + 30, r.center().y(), 90, .7, (80, 230, 255)))
                else:
                    L.append((r.x() - 4, r.center().y(), 36, .4 * (1 if (t * 1.2) % 1 < .6 else .5),
                              (90, 255, 150) if fixed else (255, 60, 60)))
            elif k == "fuse":
                L.append((cx, r.y(), 44, .7, (200, 120, 255)))
            elif k == "echo":
                L.append((cx, r.center().y(), 52, .5, (80, 230, 255)))
            elif k == "arch":
                L.append((cx, r.center().y(), 55, .55, (120, 230, 255)))
            elif k in ("glyphs", "sigil"):
                L.append((cx, r.center().y(), 42, .4, (200, 110, 255)))
            elif k == "beacon":
                L.append((cx, r.y() + 20, 100, (.3, .8, .95)[f], ((255, 170, 70), (80, 230, 255), (200, 100, 255))[f]))
            elif k == "oldradio" and fixed:
                L.append((cx, r.center().y(), 52, .55 + .1 * math.sin(t * 4), (255, 190, 110)))
            elif k == "notebook":
                L.append((cx, r.y() + 6, 46, .35, (255, 200, 120)))
            elif k == "secdoor":
                opened = "archive_open" in self.flags
                L.append((r.right() + 30, r.center().y(), 90, .65, (255, 190, 110)) if opened else
                         (r.x() - 4, r.center().y(), 40, .45 * (1 if (t * 1.5) % 1 < .6 else .4), (255, 60, 60)))
            elif k == "receiver":
                L.append((cx, r.y() + 30, 110 if "p3_done" in self.flags else 60, .9 if "p3_done" in self.flags else .35, (80, 230, 255)))
        if self.lights_on:
            L.append((150, 112, 130, .8 * ceiling_flicker(t, 1.0), (255, 232, 180)))
            L.append((310, 120, 115, .7 * ceiling_flicker(t, 4.0), (255, 232, 180)))
        for (wx, wy, w, h) in self.world.windows:
            L.append((wx + w / 2 + 14, 112, 52, .22 + .28 * self.flash, (110, 150, 255)))
        return [(x, y, r, b, _shade(c, f)) for (x, y, r, b, c) in L]

    def _draw_lighting(self, p, cx, cy, f):
        lights = self._lights(f)
        d = QPainter(self.dark)
        d.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        dc = DARK[f]
        d.fillRect(0, 0, W, H, QColor(dc[0], dc[1], dc[2], int(self.amb)))
        d.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        d.setPen(Qt.PenStyle.NoPen)
        for (x, y, r, b, _) in lights:
            g = QRadialGradient(x - cx, y - cy, r)
            g.setColorAt(0, QColor(0, 0, 0, int(255 * min(1, b))))
            g.setColorAt(.55, QColor(0, 0, 0, int(255 * min(1, b) * .45)))
            g.setColorAt(1, QColor(0, 0, 0, 0))
            d.setBrush(QBrush(g))
            d.drawEllipse(QPointF(x - cx, y - cy), r, r)
        d.end()
        p.drawImage(0, 0, self.dark)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        p.setPen(Qt.PenStyle.NoPen)
        for (x, y, r, b, c) in lights:
            if not c:
                continue
            g = QRadialGradient(x - cx, y - cy, r)
            g.setColorAt(0, QColor(c[0], c[1], c[2], int(70 * min(1, b))))
            g.setColorAt(1, QColor(c[0], c[1], c[2], 0))
            p.setBrush(QBrush(g))
            p.drawEllipse(QPointF(x - cx, y - cy), r, r)
        p.translate(-cx, -cy)
        draw_beams(p, self.world, self.t, self.flash, f)
        self.fx.draw(p, True)
        # radio-wave rings radiating from the player
        p.setBrush(Qt.BrushStyle.NoBrush)
        tc = TINT[f]
        for (rx, ry, age) in self.rings:
            a = int(150 * (1 - age / 110))
            p.setPen(QPen(QColor(tc[0], tc[1], tc[2], a), 1))
            p.drawEllipse(QPointF(rx, ry), age, age * .6)
        self._draw_outlines(p, f)
        p.translate(cx, cy)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.drawImage(0, 0, self.vignette)
        p.fillRect(0, 0, W, H, QColor(tc[0], tc[1], tc[2], 12 if f == 0 else 26))   # colour grade

    # ------------------------------------------------------------------ draw
    def _draw_outlines(self, p, f):
        """Glowing outlines on interactive objects near the player; the one you can use pulses
        brightly with corner brackets and a bobbing arrow."""
        t, pl = self.t, self.player
        pulse = .65 + .35 * math.sin(t * 5)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for pr in self.world.props:
            if not (pr.visible(f, self.flags) and pr.interactive_in(f)):
                continue
            if OPEN_FLAG.get(pr.action) in self.flags:
                continue
            c = pr.rect.center()
            focus = pr is self.focus
            if not focus and math.hypot(c.x() - pl.x, c.y() - pl.y) > 70:
                continue
            k = pulse if focus else .28
            r = pr.rect.adjusted(-2, -2, 2, 2)
            col = (255, 200, 90) if focus else (120, 220, 255)
            for wd, al in ((4, 34), (2, 70), (1, 190)):
                p.setPen(QPen(QColor(col[0], col[1], col[2], int(al * k)), wd))
                p.drawRect(r)
            if focus:
                s = 5
                p.setPen(QPen(QColor(255, 235, 170, 230), 1))
                for (bx, by, dx, dy) in ((r.left(), r.top(), 1, 1), (r.right(), r.top(), -1, 1),
                                         (r.left(), r.bottom(), 1, -1), (r.right(), r.bottom(), -1, -1)):
                    p.drawLine(QPointF(bx, by), QPointF(bx + dx * s, by))
                    p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * s))
                ay = r.top() - 9 + math.sin(t * 6) * 2
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(255, 210, 100, 230))
                p.drawPolygon(QPolygonF([QPointF(c.x() - 4, ay), QPointF(c.x() + 4, ay), QPointF(c.x(), ay + 5)]))
                p.setBrush(Qt.BrushStyle.NoBrush)

    def _paint_world(self, img, f, cx, cy):
        """Render the whole world as it exists on frequency f into img."""
        self.vf = f
        q = QPainter(img)
        q.fillRect(0, 0, W, H, QColor(6, 8, 16))
        q.save()
        q.translate(-cx, -cy)
        q.drawImage(0, 0, self.world.bg)
        if f in self.world.overlays:
            q.setOpacity(.75 + .25 * math.sin(self.t * 2))
            q.drawImage(0, 0, self.world.overlays[f])
            q.setOpacity(1)
        draw_windows(q, self.world, self.t, self.flash, f)
        q.setPen(Qt.PenStyle.NoPen)
        for m in self.dust:
            q.fillRect(int(m[0]), int(m[1]), 1, 1, QColor(190, 205, 230, 90))
        self.fx.draw(q, False)
        items = [(pr.sort_y, 0, pr) for pr in self.world.props if pr.visible(f, self.flags)]
        items.append((self.player.y, 1, self.player))
        items.sort(key=lambda i: (i[0], i[1]))
        for _, _, o in items:
            if o is self.player:
                o.draw(q, self.t)
            else:
                draw_prop(q, o, self.t, self)
        q.restore()
        self._draw_lighting(q, cx, cy, f)
        q.end()

    def draw(self, p):
        cx, cy = int(round(self.cam[0])), int(round(self.cam[1]))
        u = self.trans_t / TRANS_TIME
        transitioning = u < 1.0
        if transitioning:
            self._paint_world(self.cv_old, self.old_freq, cx, cy)
            self._paint_world(self.cv_new, self.freq, cx, cy)
            q = QPainter(self.cv_mix)
            q.drawImage(0, 0, self.cv_old)
            sx, sy = self.player.x - cx, self.player.y - 12 - cy
            rad = (u ** .8) * 340
            path = QPainterPath()
            path.addEllipse(QPointF(sx, sy), rad, rad)
            q.setClipPath(path)
            q.drawImage(0, 0, self.cv_new)
            q.setClipping(False)
            tc = TINT[self.freq]
            q.setBrush(Qt.BrushStyle.NoBrush)
            for wd, al in ((7, 40), (3, 120), (1, 255)):
                q.setPen(QPen(QColor(tc[0], tc[1], tc[2], int(al * (1 - u))), wd))
                q.drawEllipse(QPointF(sx, sy), rad, rad)
            q.end()
            src = self.cv_mix
        else:
            self._paint_world(self.cv_new, self.freq, cx, cy)
            src = self.cv_new
        self._composite(p, src, u)
        if self.zone_fade < 1.0:                     # room-to-room fade: dip to dark and back, HUD stays readable
            p.fillRect(0, 0, W, H, QColor(0, 0, 0, int(215 * math.sin(math.pi * self.zone_fade))))
        self._draw_hud(p, cx, cy)
        if self.fade > 0:
            p.fillRect(0, 0, W, H, QColor(0, 0, 0, int(255 * min(1.0, self.fade))))

    def _composite(self, p, src, u):
        """Copy the world to the screen with radio distortion (scanline shear) and static."""
        amp = 0.0
        if u < 1.0:
            amp += (1 - u) ** 1.5 * 9
        if self.radio_on:
            amp += .5 + 1.2 * (1 - self.signal)
        amp += self.shift * 8                       # reality shift: the picture tears
        if amp < .35:
            p.drawImage(0, 0, src)
        else:
            sh = 6
            bands = {}
            for gy, gh, go in self.glitch:
                k = (1 - u) if u < 1.0 else self.shift
                if k > 0:
                    for y in range(gy // sh, (gy + gh) // sh + 1):
                        bands[y] = go * k
            for i in range(0, H, sh):
                off = int(amp * math.sin(self.t * 9 + i * .11) * .5 + bands.get(i // sh, 0))
                p.drawImage(QRectF(off, i, W, sh), src, QRectF(0, i, W, sh))
        if self.shift > 0:                          # the layer it is slipping into
            tc = TINT[(self.freq + 1 + int(self.t * 3) % 2) % 3]
            p.fillRect(0, 0, W, H, QColor(tc[0], tc[1], tc[2], int(60 * self.shift)))
        n = int(self.statics * 320 + (12 + 45 * (1 - self.signal) if self.radio_on else 0))
        rr = random.random
        for _ in range(n):
            g = int(120 + 135 * rr())
            p.fillRect(int(rr() * W), int(rr() * H), 1 + int(rr() * 3), 1, QColor(g, g, g, int(40 + 90 * rr())))
        if u < 1.0:
            tc = TINT[self.freq]
            p.fillRect(0, int(u * H) - 1, W, 3, QColor(tc[0], tc[1], tc[2], int(140 * (1 - u))))
            p.fillRect(0, 0, W, H, QColor(tc[0], tc[1], tc[2], int(70 * max(0, 1 - u * 4))))

    # ------------------------------------------------------------------ HUD
    def _draw_hud(self, p, cx, cy):
        if self.frozen:       # a puzzle screen is open and draws its own interface
            return
        t = self.t
        ui.panel(p, 6, 6, 214, 46, CYAN)
        p.fillRect(13, 14, 4, 4, QColor(80, 230, 255, 140 + int(100 * math.sin(t * 3))))
        ui.text(p, self.zone, 22, 19, CYAN, 8, True)
        hh, mm = divmod(int(self.minutes), 60)
        ui.text(p, f"{hh % 24:02d}:{mm:02d} AM", 160, 19, DIM, 8)
        glow = QColor(255, 235, 170) if self.mission_toast > 0 else TEXT
        ui.text(p, self.objective(), 13, 34, glow, 7, self.mission_toast > 0)
        ui.text(p, self.hint(), 13, 46, DIM, 6)
        self._draw_radio(p)
        self.tutorial.draw(p, self)
        self._draw_echo_widget(p)
        self._draw_marker(p, cx, cy)
        self._draw_item_banner(p)
        self._draw_debug(p)

        if self.banner > 0:
            a = int(255 * min(1, self.banner))
            ui.text(p, self.zone, W / 2, 100, QColor(80, 230, 255, a), 16, True, True, True)

        if self.dialog:
            self.dialog.draw(p, self.t)
            return
        if self.toast_t > 0:
            ui.text(p, self.toast, W / 2, 222, QColor(255, 200, 100, int(255 * min(1, self.toast_t))), 8, True, True)
        if self.focus:
            pr = self.focus
            spec = pr.spec(self.freq)
            label = f"[E]  {spec['verb']} {spec['name']}"
            if pr.action == "door" and "fixed" in self.flags:
                label = f"[E]  Send {FREQS[self.freq]} MHz tone"
            wpx = len(label) * 6 + 24
            bob = math.sin(t * 6) * 1.5
            ui.panel(p, W / 2 - wpx / 2, 232 + bob, wpx, 22, AMBER)
            ui.text(p, label, W / 2, 247 + bob, AMBER, 8, True, True, True)
        else:
            f = self.flags
            parts = [s for s, flag in (("WASD move", "tut_move"), ("E interact", "tut_interact"), ("SPACE radio", "radio_used"),
                                       ("Q tune", "tuned"), ("R echo", "echo_opened"), ("J journal", "journal_opened"),
                                       ("ESC pause", "pause_opened")) if flag in f]
            if parts:
                ui.text(p, "   ".join(parts), W / 2, H - 6, DIM, 7, False, True)

    def _draw_echo_widget(self, p):
        """Mini signal tracker (bottom-left) shown while the Echo Receiver is tracking."""
        if "echo_track" not in self.flags:
            return
        band, t = self.eff, self.t
        col = QColor(*TINT[band])
        x, y, w, h = 6, H - 50, 112, 42
        ui.panel(p, x, y, w, h, col)
        ui.text(p, "ECHO", x + 6, y + 11, col, 7, True)
        ui.text(p, f"{FREQS[band]}", x + 36, y + 11, DIM, 7)
        n = self.nearest(band)
        s = self.strength(band)
        if n is None:
            others = [FREQS[b] for b in range(3) if b != band and self.targets(b)]
            ui.text(p, "NO SIGNAL HERE", x + 6, y + 26, DIM, 7)
            if others:
                ui.text(p, "Try " + " / ".join(str(o) for o in others) + " MHz  [Q]", x + 6, y + 37, AMBER, 6)
            return
        ang = math.atan2(n[2], n[1])
        cx, cy = x + 20, y + 28
        p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), 90), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 9, 9)
        r = 4 + 5 * s
        tip = QPointF(cx + math.cos(ang) * 8, cy + math.sin(ang) * 8)
        p.setPen(QPen(QColor(255, 255, 255, 230), 1))
        p.drawLine(QPointF(cx, cy), tip)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(tip, 1.5, 1.5)
        for i in range(8):
            on = i < int(round(s * 8))
            c = QColor(90, 255, 150) if i < 5 else QColor(255, 176, 60) if i < 7 else QColor(255, 80, 80)
            p.fillRect(x + 40 + i * 8, y + 36 - (3 + i), 6, 3 + i, c if on else QColor(34, 40, 54))
        if s > .8 and int(t * 5) % 2 == 0:
            ui.text(p, "LOCK", x + 42, y + 11 + 0, GREEN, 6, True)

    def _draw_marker(self, p, cx, cy):
        """While the Echo is tracking: a bobbing marker over the nearest hidden signal, or an edge arrow pointing to it."""
        if "echo_track" not in self.flags:
            return
        n = self.nearest(self.eff)
        if n is None:
            return
        sx, sy = self.player.x + n[1] - cx, self.player.y + n[2] - cy
        col = QColor(*TINT[self.eff])
        bob = math.sin(self.t * 5) * 2
        if 8 < sx < W - 8 and 8 < sy < H - 8:
            p.setPen(QPen(col, 1))
            p.setBrush(QColor(col.red(), col.green(), col.blue(), 90))
            p.drawPolygon(QPolygonF([QPointF(sx, sy - 18 + bob), QPointF(sx - 4, sy - 24 + bob), QPointF(sx + 4, sy - 24 + bob)]))
            return
        mx, my = max(14, min(W - 14, sx)), max(70, min(H - 24, sy))
        ang = math.atan2(sy - self.player.y + cy, sx - self.player.x + cx)
        pts = [QPointF(mx + math.cos(ang + a) * r, my + math.sin(ang + a) * r) for a, r in ((0, 9), (2.5, 7), (-2.5, 7))]
        p.setPen(QPen(col, 1))
        p.setBrush(QColor(col.red(), col.green(), col.blue(), 150 + int(80 * math.sin(self.t * 6))))
        p.drawPolygon(QPolygonF(pts))

    def _draw_debug(self, p):
        """Developer overlay (F3). Only available when the game is started with TLS_DEBUG=1."""
        if not self.debug:
            return
        from ..chapters import CHAPTERS  # noqa
        ch, m = self.story.chapter(), self.story.mission()
        lines = [f"CH{ch.n} {ch.title}  freq={FREQS[self.freq]} eff={FREQS[self.eff]} radio={'on' if self.radio_on else 'off'}",
                 "mission: " + (m.id if m else "-") + "  hint: " + self.hint(),
                 "done: " + ",".join(x.id for x in ch.missions if "m_" + x.id in self.flags),
                 "chapter complete: " + str("ch%d_done" % ch.n in self.flags) + "  can finish now: " + str(all(x.done(self) for x in ch.missions)),
                 "puzzles: " + ",".join(sorted(f for f in self.flags if f.endswith("_done") or f in ("src_tut", "fixed", "beacon")))]
        if m:
            miss = [fl for fl in ("echo_found", "tut_move", "entered", "echo_track", "src_tut", "tut_done") if fl not in self.flags]
            lines.append("missing flags: " + ",".join(miss))
        p.fillRect(0, H - 70, W, 70, QColor(0, 0, 0, 190))
        for i, ln in enumerate(lines):
            ui.text(p, ln, 4, H - 62 + i * 11, QColor(120, 255, 140), 6)

    def _draw_item_banner(self, p):
        """Big 'item acquired' card with the device art, right after picking up the Echo Receiver."""
        if self.item_banner <= 0:
            return
        from ..echo import draw_device
        a = min(1.0, self.item_banner, (4.0 - self.item_banner) * 3)
        p.save()
        p.setOpacity(max(0.0, a))
        p.fillRect(0, 64, W, 100, QColor(0, 0, 10, 200))
        p.fillRect(0, 64, W, 1, QColor(80, 230, 255, 160)); p.fillRect(0, 163, W, 1, QColor(80, 230, 255, 160))
        draw_device(p, 70, 74, 1, self.t, 1, .6, 0)
        ui.text(p, "ITEM ACQUIRED", 150, 96, DIM, 8, True)
        ui.text(p, "THE ECHO RECEIVER", 150, 118, CYAN, 15, True, False, True)
        ui.text(p, "Detects hidden signals. Press R to open it.", 150, 138, TEXT, 8)
        ui.text(p, "SCAN  /  TRACK  /  MEMORY", 150, 152, AMBER, 7, True)
        p.restore()

    def _draw_radio(self, p):
        t = self.t
        x, y, w = W - 182, 6, 176
        if not self.radio_on:
            blink = "radio_used" not in self.flags and int(t * 2) % 2 == 0
            ui.panel(p, x, y, w, 22, DIM)
            ui.text(p, "RADIO OFF", x + 8, y + 15, DIM, 8, True)
            ui.text(p, "[SPACE] activate", x + 82, y + 15, AMBER if blink else DIM, 7)
            return
        f = self.idx
        col = QColor(*TINT[f])
        ui.panel(p, x, y, w, 68, col)
        ui.text(p, "RADIO", x + 8, y + 13, DIM, 7, True)
        p.fillRect(x + 44, y + 8, 4, 4, QColor(col.red(), col.green(), col.blue(), 120 + int(120 * math.sin(t * 8))))
        ui.text(p, f"{self.dial:5.1f}", x + 8, y + 36, col, 16, True, glow=True)
        ui.text(p, "MHz", x + 72, y + 36, DIM, 7)
        ui.text(p, FREQ_NAMES[f], x + 8, y + 48, col, 8, True)
        # signal strength: 8 bars
        ui.text(p, "SIGNAL", x + 112, y + 13, DIM, 7, True)
        lit = int(round(self.signal * 8))
        for i in range(8):
            bh = 3 + i
            c = (QColor(90, 255, 150) if i < 5 else AMBER if i < 7 else QColor(255, 80, 80)) if i < lit else QColor(34, 40, 54)
            p.fillRect(x + 112 + i * 7, y + 32 - bh, 5, bh, c)
        tuning = abs(FREQS[f] - self.dial) > .4
        if tuning:
            ui.text(p, "TUNING" + "." * (int(t * 6) % 4), x + 112, y + 46, AMBER, 7, True)
        elif self.signal > .75:
            ui.text(p, "SIGNAL FOUND", x + 112, y + 46, GREEN, 7, True, glow=True)
        else:
            ui.text(p, "LOCKED", x + 112, y + 46, col, 7, True)
        # tuning scale 86..124 with the three station marks and the needle
        sx0, sw = x + 8, w - 16
        p.fillRect(sx0, y + 60, sw, 1, QColor(60, 70, 90))
        for v in range(86, 125, 2):
            px = sx0 + (v - 86) / 38 * sw
            p.fillRect(int(px), y + 58 if v % 10 else y + 56, 1, 3 if v % 10 else 5, QColor(70, 82, 104))
        for i, fv in enumerate(FREQS):
            px = sx0 + (fv - 86) / 38 * sw
            p.fillRect(int(px) - 1, y + 54, 3, 3, QColor(*TINT[i]))
        nx = sx0 + max(0, min(1, (self.dial - 86) / 38)) * sw
        p.fillRect(int(nx), y + 53, 1, 12, QColor(255, 255, 255, 230))
        ui.text(p, "[Q] tune   [SPACE] off", x + 8, y + 82, DIM, 7)
