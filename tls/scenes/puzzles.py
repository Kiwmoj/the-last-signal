"""Puzzle interfaces.

  ReconstructScene - The Missing Transmission: record fragments on 3 frequencies, order them.
  PasswordScene    - The Locked Archive: type the password pieced together from clues.
  ReceiverScene    - The Unknown Signal: feed three tones, heaviest pulse count first.

All three keep the world animating behind them, accept Q / SPACE for tuning, give clear
instructions, flash green/red feedback and write their completion into gp.flags (autosaved).
"""
import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..constants import CYAN, AMBER, TEXT, DIM, GREEN, RED
from ..story import (PASSWORD, CHAMBER_CODE, LOCKER_CODE, FRAG_ORDER, RADIO_FRAGMENTS, RADIO_VOICES, RADIO_RESTORED, RECEIVER_PULSES,
                     RECEIVER_ORDER, RECEIVER_DECODE, REWARD)
from ..world import FREQS, FREQ_NAMES, TINT
from .. import ui
from .overlay import Overlay, Typer, elide

FULL_MESSAGE = " ".join(RADIO_FRAGMENTS[f] for f in FRAG_ORDER)
CAPTURE_TIME = 1.6


def _frame(p, x, y, w, h, title, col, right=""):
    ui.panel(p, x, y, w, h, col)
    p.fillRect(x + 1, y + 1, w - 2, 16, QColor(col.red() // 6, col.green() // 6, col.blue() // 6))
    ui.text(p, title, x + 8, y + 13, col, 8, True, glow=True)
    if right:
        ui.text(p, right, x + w - 10 - int(len(right) * 6.6), y + 13, col, 8, True)


# =====================================================================================
# PUZZLE 1: THE MISSING TRANSMISSION
# =====================================================================================
class ReconstructScene(Overlay):
    def __init__(self, game, gp):
        super().__init__(game, gp)
        self.slots = []
        self.sel = 0
        self.cap = 0.0
        self.msg, self.msg_col, self.msg_t = "", TEXT, 0.0
        self.shake = 0.0
        self.typer = Typer(FULL_MESSAGE, 55) if "p1_done" in gp.flags else None
        self.audio.play("click")

    @property
    def solved(self):
        return "p1_done" in self.gp.flags

    def say(self, text, col, secs=3.0):
        self.msg, self.msg_col, self.msg_t = text, col, secs

    def tick(self, dt):
        gp = self.gp
        self.msg_t = max(0.0, self.msg_t - dt)
        self.shake = max(0.0, self.shake - dt)
        if self.typer and self.typer.update(dt):
            self.audio.play("blip", .35)
        if self.solved:
            return
        # Recording: the radio has to be ON and settled on a band that has not been captured yet.
        # The faint old-radio signal can only be locked with the Echo Receiver.
        f = gp.eff
        has_echo = "echo_found" in gp.flags
        ready = has_echo and gp.radio_on and gp.freq == f and gp.trans_t >= .8 and f not in gp.frags
        if ready:
            self.cap += dt / CAPTURE_TIME
            if self.cap >= 1.0:
                self.cap = 0.0
                gp.frags.add(f)
                gp.journal.add(f"frag_{f}", f"Radio fragment ({FREQS[f]} MHz)",
                               f"Old Radio, {FREQ_NAMES[f].lower()}: \"{RADIO_FRAGMENTS[f]}\"")
                gp.record(f"frag_{f}", f, f"Old Radio fragment ({FREQS[f]} MHz)", RADIO_FRAGMENTS[f])
                self.say(f"FRAGMENT RECORDED: {FREQS[f]} MHz", GREEN)
                self.audio.play("ok")
                self.sel = f
        else:
            self.cap = max(0.0, self.cap - dt * 2)

    def key_press(self, k):
        K, gp = Qt.Key, self.gp
        if k == K.Key_Escape:
            self.close()
        elif self.tune_key(k):
            pass
        elif self.solved:
            if k in (K.Key_Return, K.Key_Enter) and self.typer:
                self.typer.finish()
        elif k in (K.Key_W, K.Key_Up):
            self.sel = (self.sel - 1) % 3
            self.audio.play("click", .4)
        elif k in (K.Key_S, K.Key_Down):
            self.sel = (self.sel + 1) % 3
            self.audio.play("click", .4)
        elif k == K.Key_Backspace:
            if self.slots:
                self.slots.pop()
                self.audio.play("click", .4)
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E):
            if len(self.slots) == 3:
                self.submit()
            elif self.sel not in gp.frags:
                self.say("That fragment is not recorded yet. Tune to its band and hold.", AMBER)
                self.audio.play("bad", .5)
            elif self.sel in self.slots:
                self.say("Already placed. BACKSPACE removes the last fragment.", AMBER)
            else:
                self.slots.append(self.sel)
                self.audio.play("click")

    def submit(self):
        if self.slots == FRAG_ORDER:
            self.gp.complete("p1_done", "The Missing Transmission",
                             "The message is restored and Marlowe's personal log is decrypted on the terminal. " + RADIO_RESTORED[1])
            self.typer = Typer(FULL_MESSAGE, 55)
            self.say("TRANSMISSION RESTORED", GREEN, 6)
        else:
            self.slots = []
            self.shake = .5
            self.say("SIGNAL DESYNC. The fragments do not connect. Try another order.", RED)
            self.audio.play("bad")

    # ------------------------------------------------------------------ drawing
    def draw(self, p):
        gp, t = self.gp, self.t
        f = gp.eff
        tint = QColor(*TINT[f])
        p.save()
        ui.overlay_open(p, t, 175)
        ox = int(math.sin(t * 90) * 3 * (self.shake / .5)) if self.shake > 0 else 0
        x, y, w, h = 22 + ox, 14, 436, 242
        _frame(p, x, y, w, h, "OLD RADIO  //  TRANSMISSION RECONSTRUCTOR", tint,
               f"{gp.dial:5.1f} MHz" if gp.radio_on else "RADIO OFF")
        if self.solved:
            self._draw_solved(p, x, y, w, h, tint)
        else:
            self._draw_puzzle(p, x, y, w, h, tint)
        if self.msg_t > 0:
            ui.text(p, self.msg, x + w / 2, y + h - 22, QColor(self.msg_col.red(), self.msg_col.green(), self.msg_col.blue(),
                                                               int(255 * min(1, self.msg_t))), 8, True, True, True)
        p.restore()

    def _draw_puzzle(self, p, x, y, w, h, tint):
        gp, t = self.gp, self.t
        f = gp.eff
        ui.type_lines(p, "A broken transmission is scattered across THREE frequencies. Turn the radio on (SPACE) and TUNE (Q) to each band, "
                         "then hold it to RECORD that band's fragment with your Echo Receiver. Finally ARRANGE the fragments in the order that makes "
                         "the message make sense, and TRANSMIT. Recordings are kept in the receiver's MEMORY [R].", 99999, x + 12, y + 32, w - 24, TEXT, 7, 9)
        # scope + capture meter
        sx, sy = x + 12, y + 70
        locking = self.cap > 0 or f in gp.frags
        noise = 0.05 if f in gp.frags else max(.05, .7 - self.cap * .65) if gp.radio_on else .9
        ui.scope(p, sx, sy, 150, 50, t, tint if gp.radio_on else QColor(90, 90, 100), .8, noise)
        p.fillRect(sx, sy + 56, 150, 7, QColor(14, 20, 32))
        if f in gp.frags:
            p.fillRect(sx, sy + 56, 150, 7, QColor(60, 200, 110))
            ui.text(p, "RECORDED", sx + 2, sy + 74, GREEN, 7, True)
        else:
            p.fillRect(sx, sy + 56, int(150 * self.cap), 7, tint)
            state = "RECORDING..." if self.cap > 0 else ("TUNE IN AND HOLD" if gp.radio_on else "RADIO OFF - PRESS SPACE")
            ui.text(p, state, sx + 2, sy + 74, tint if self.cap > 0 else AMBER, 7, True)
        ui.text(p, f"BAND: {FREQS[f]} MHz  {FREQ_NAMES[f]}", sx, sy + 87, DIM, 7)
        # fragment list
        lx = x + 180
        ui.text(p, "FRAGMENTS", lx, y + 78, DIM, 7, True)
        for i in range(3):
            yy = y + 90 + i * 18
            have = i in gp.frags
            on = i == self.sel
            if on:
                p.fillRect(lx - 4, yy - 10, w - 192, 16, QColor(40, 70, 100, 170))
            c = QColor(*TINT[i])
            p.fillRect(lx, yy - 7, 3, 9, c)
            ui.text(p, f"{FREQS[i]}", lx + 8, yy, c, 8, True)
            ui.text(p, elide(RADIO_FRAGMENTS[i], w - 270, 7) if have else "- not recorded -",
                    lx + 52, yy, TEXT if have else DIM, 7)
        # order slots
        ui.text(p, "ORDER", lx, y + 158, DIM, 7, True)
        sw = (w - 192) // 3 - 4
        for i in range(3):
            bx = lx + i * (sw + 6)
            filled = i < len(self.slots)
            col = QColor(*TINT[self.slots[i]]) if filled else QColor(60, 70, 90)
            p.fillRect(bx, y + 164, sw, 28, QColor(10, 16, 26))
            p.setPen(col)
            p.drawRect(bx, y + 164, sw - 1, 27)
            ui.text(p, str(i + 1), bx + 3, y + 174, DIM, 6)
            if filled:
                ui.text(p, elide(RADIO_FRAGMENTS[self.slots[i]], sw - 8, 6), bx + 5, y + 186, TEXT, 6)
        if len(self.slots) == 3 and int(t * 3) % 2 == 0:
            ui.text(p, "[ENTER] TRANSMIT", lx, y + 206, GREEN, 8, True, glow=True)
        ui.text(p, "Q tune  SPACE radio  W/S pick  ENTER place  BKSP undo  ESC leave", x + 12, y + h - 7, DIM, 7)

    def _draw_solved(self, p, x, y, w, h, tint):
        gp, t = self.gp, self.t
        f = gp.eff
        ui.text(p, "MESSAGE RESTORED", x + 12, y + 36, GREEN, 9, True, glow=True)
        ui.scope(p, x + w - 162, y + 24, 150, 20, t, QColor(90, 255, 150), .8, .02)
        ui.type_lines(p, '"' + self.typer.text + '"', self.typer.shown + 1, x + 14, y + 60, w - 28, QColor(220, 240, 255), 8, 12)
        yy = y + 120
        ui.text(p, f"ALSO ON THIS BAND ({FREQS[f]} MHz {FREQ_NAMES[f]})", x + 14, yy, DIM, 7, True)
        ui.type_lines(p, RADIO_VOICES[f], 99999, x + 14, yy + 14, w - 28, tint, 8, 12, glitch=.05 if f == 2 else 0.0, t=t)
        ui.text(p, RADIO_RESTORED[0], x + 14, y + 186, GREEN, 7)
        ui.text(p, "Tune to other bands (Q) to hear more.   ESC leave", x + 12, y + h - 7, DIM, 7)


# =====================================================================================
# PUZZLE 2: THE LOCKED ARCHIVE
# =====================================================================================
ARCHIVE_CFG = dict(
    title="ARCHIVE DOOR  //  STATION 09", answer=PASSWORD, digits_only=False, maxlen=12, flag="archive_open",
    puzzle_title="The Locked Archive",
    intro="The keypad wants a PASSPHRASE. Marlowe hid the pieces around the station, on different frequencies. "
          "Type letters and digits, then press ENTER.",
    hint="SYSTEM HINT: Marlowe chose something personal. Think of family, and when.",
    notes=("key_name", "key_year", "key_format", "key_password"),
    notes_empty="Nothing yet. Try the terminal and the research notebook. Their pages differ on each frequency.",
    key_id="key_password", key_title=f"Archive password: {PASSWORD}",
    key_text=f"The archive door opened with {PASSWORD}: the name NORA and the year 1971.",
    who="ARCHIVE DOOR",
    granted=["ACCESS GRANTED. The bolts retract one by one and the archive door grinds open.",
             "Beyond: shelves of recordings, and one enormous receiver, silent and waiting."])
CHAMBER_CFG = dict(
    title="CHAMBER DOOR  //  TRANSMISSION CHAMBER", answer=CHAMBER_CODE, digits_only=True, maxlen=6, flag="chamber_open",
    puzzle_title="The Chamber Lock",
    intro="The keypad wants the DATE everything began, as six digits: day, month, year. The station wrote it down in three places, "
          "one in each layer of itself. Type digits, then press ENTER.",
    hint="SYSTEM HINT: three plaques. The present holds the day, the past the month, the unknown the year. Check the incident report.",
    notes=("date_day", "date_month", "date_year", "incident_hint"),
    notes_empty="Nothing yet. The incident report on the terminal says where the date is written.",
    key_id="key_chamber", key_title=f"Chamber code: {CHAMBER_CODE}",
    key_text=f"The chamber door opened with {CHAMBER_CODE}: 14 08 80, the 14th of August, 1980.",
    who="CHAMBER DOOR",
    granted=["ACCESS GRANTED. The date unlocks the chamber, and the massive door slides open.",
             "A low hum rolls out, matching the pulse of whatever waits inside."])


LOCKER_CFG = dict(
    title="STAFF LOCKER 2-A  //  OFFICES", answer=LOCKER_CODE, digits_only=True, maxlen=4, flag="locker_open",
    puzzle_title="Staff Locker 2-A",
    intro="A four-digit dial lock. One digit was left in each of several rooms, and each only reads clearly on one frequency. "
          "Type digits in order, then press ENTER.",
    hint="SYSTEM HINT: digit 1 is on the Control Room duty board (104.7). Digits 2 and 3 are on the Offices whiteboard (88.1, then 121.3). Digit 4 is on the Research Wing slate (88.1).",
    notes=("lk_rule", "lk_1", "lk_2", "lk_3", "lk_4"),
    notes_empty="Nothing yet. Start with the duty board in the Control Room.",
    key_id="key_locker", key_title=f"Locker 2-A code: {LOCKER_CODE}",
    key_text=f"Locker 2-A opened with {LOCKER_CODE}: one digit from each of the notes left around the station.",
    who="LOCKER 2-A",
    granted=["CLICK. The dial gives, and the locker door swings open with a groan.",
             "Inside: a folded letter, and a small maintenance tape labelled 'THE NIGHT IT BEGAN'."],
    extra=[("elias_letter", "Elias's unsent letter",
            "'Nora, if the experiment works, I will hear your voice again. If it fails, know that I never stopped listening. "
            "I hid the date where the station would show it to anyone who listened closely: one layer each. I should have burned the archive.'", "clue")],
    tape=("locker_tape", 1, "Maintenance tape 2-A",
          "WREN: 'Three thirty-three. Elias has the archive open and he will not stop. The receiver is answering, and the voice on it is not one of ours.'"))


class PasswordScene(Overlay):
    """Keypad screen for the archive password and the chamber date code (configured by a cfg dict)."""

    def __init__(self, game, gp, cfg=None):
        super().__init__(game, gp)
        self.cfg = cfg or ARCHIVE_CFG
        self.MAXLEN = self.cfg["maxlen"]
        self.text = ""
        self.attempts = 0
        self.msg, self.msg_col = "", TEXT
        self.shake = 0.0
        self.granted = 0.0
        self.audio.play("click")

    def tick(self, dt):
        self.shake = max(0.0, self.shake - dt)
        if self.granted > 0:
            self.granted -= dt
            if self.granted <= 0:
                self.close()
                self.gp.open_dialog(self.cfg["who"], self.cfg["granted"], "terminal")

    def key_press(self, k):
        K = Qt.Key
        k = int(k)
        if self.granted > 0:
            return
        if k == K.Key_Escape:
            self.close()
        elif k == K.Key_Backspace:
            self.text = self.text[:-1]
            self.audio.play("click", .4)
        elif k in (K.Key_Return, K.Key_Enter):
            self.submit()
        elif ((65 <= k <= 90 and not self.cfg["digits_only"]) or 48 <= k <= 57) and len(self.text) < self.MAXLEN:
            self.text += chr(k)
            self.audio.play("click", .6)

    def submit(self):
        if not self.text:
            return
        cfg = self.cfg
        if self.text == cfg["answer"]:
            gp = self.gp
            gp.complete(cfg["flag"], cfg["puzzle_title"], REWARD[cfg["flag"]])
            gp.journal.add(cfg["key_id"], cfg["key_title"], cfg["key_text"], "key")
            for e in cfg.get("extra", ()):
                gp.journal.add(*e)
            if cfg.get("tape"):
                gp.record(*cfg["tape"])
            self.msg, self.msg_col, self.granted = "ACCESS GRANTED", GREEN, 1.6
            self.audio.play("door")
        else:
            self.attempts += 1
            self.msg, self.msg_col, self.shake = "ACCESS DENIED", RED, .5
            self.text = ""
            self.audio.play("bad")

    def draw(self, p):
        gp, t, cfg = self.gp, self.t, self.cfg
        p.save()
        ui.overlay_open(p, t, 185)
        ox = int(math.sin(t * 90) * 3 * (self.shake / .5)) if self.shake > 0 else 0
        ok = self.granted > 0
        col = GREEN if ok else AMBER
        x, y = 28 + ox, 24
        _frame(p, x, y, 262, 214, cfg["title"], col)
        ui.type_lines(p, cfg["intro"], 99999, x + 10, y + 32, 242, TEXT, 7, 9)
        # status lamp + attempts
        lamp = GREEN if ok else (RED if (self.shake > 0 or int(t * 2) % 2 == 0) else QColor(90, 30, 30))
        p.fillRect(x + 10, y + 72, 10, 10, lamp)
        ui.text(p, self.msg or "LOCKED", x + 26, y + 81, self.msg_col if self.msg else DIM, 8, True, glow=bool(self.msg))
        ui.text(p, f"ATTEMPTS {self.attempts}", x + 190, y + 81, DIM, 7)
        # entry boxes
        for i in range(self.MAXLEN):
            bx = x + 10 + i * 20
            p.fillRect(bx, y + 94, 18, 24, QColor(8, 12, 20))
            p.setPen(col if i == len(self.text) and int(t * 2) % 2 == 0 else QColor(70, 80, 100))
            p.drawRect(bx, y + 94, 17, 23)
            if i < len(self.text):
                ui.text(p, self.text[i], bx + 4, y + 112, col, 12, True, glow=True)
        if self.attempts >= 3:
            ui.type_lines(p, cfg["hint"], 99999, x + 10, y + 138, 242, AMBER, 7, 9)
        ui.text(p, "BKSP delete   ENTER submit   ESC leave", x + 10, y + 206, DIM, 6)
        # discovered fragments, pulled from the journal's KEYS
        _frame(p, x + 270, y, 140, 214, "KNOWN PIECES", CYAN)
        keys = [e for e in gp.journal.by_cat("key") if e["id"] in cfg["notes"]]
        yy = y + 32
        if not keys:
            ui.type_lines(p, cfg["notes_empty"], 99999, x + 278, yy, 126, DIM, 7, 9)
        for e in keys:
            ui.text(p, e["title"], x + 278, yy, AMBER, 7, True)
            yy = ui.type_lines(p, e["text"], 99999, x + 278, yy + 10, 126, TEXT, 6, 8) + 4
        p.restore()


# =====================================================================================
# PUZZLE 3: THE UNKNOWN SIGNAL
# =====================================================================================
class ReceiverScene(Overlay):
    def __init__(self, game, gp):
        super().__init__(game, gp)
        self.seq = []
        self.msg, self.msg_col, self.msg_t = "", TEXT, 0.0
        self.flash = 0.0
        self.page = 0
        self.typer = None
        if "p3_done" in gp.flags:
            self.typer = Typer(RECEIVER_DECODE[0], 60)
        self.audio.play("click")

    @property
    def active(self):
        return "p3_done" in self.gp.flags

    def tick(self, dt):
        self.msg_t = max(0.0, self.msg_t - dt)
        self.flash = max(0.0, self.flash - dt * 2)
        if self.typer and self.typer.update(dt):
            self.audio.play("blip", .35)

    def key_press(self, k):
        K, gp = Qt.Key, self.gp
        if k == K.Key_Escape:
            self.close()
        elif self.tune_key(k):
            pass
        elif self.active:
            if k in (K.Key_Return, K.Key_Enter, K.Key_E) and self.typer:
                if not self.typer.done:
                    self.typer.finish()
                elif self.page + 1 < len(RECEIVER_DECODE):
                    self.page += 1
                    self.typer = Typer(RECEIVER_DECODE[self.page], 60)
        elif k == K.Key_Backspace:
            self.seq = []
        elif k in (K.Key_Return, K.Key_Enter, K.Key_E):
            self.seq.append(gp.eff)
            self.audio.play("click")
            if len(self.seq) == 3:
                self.submit()

    def submit(self):
        gp = self.gp
        if self.seq == RECEIVER_ORDER:
            gp.complete("p3_done", "The Unknown Signal", REWARD["p3_done"])
            gp.record("decode", 1, "Receiver: Marlowe's last warning", " ".join(RECEIVER_DECODE[:2]))
            gp.journal.add("live_voice", "The live voice",
                           "Marlowe's recording ended with a live voice that spoke Alex's full name: 'You were not supposed to hear this yet.' "
                           "The Echo Receiver can track where it is coming from.")
            self.page, self.typer = 0, Typer(RECEIVER_DECODE[0], 60)
            self.flash = 1.0
        else:
            self.seq = []
            self.flash = 1.0
            self.msg, self.msg_col, self.msg_t = "SEQUENCE REJECTED. The receiver stays dormant.", RED, 3.0
            self.audio.play("bad")

    def draw(self, p):
        gp, t = self.gp, self.t
        f = gp.eff
        tint = QColor(*TINT[f])
        p.save()
        ui.overlay_open(p, t, 180)
        x, y, w, h = 22, 14, 436, 242
        act = self.active
        _frame(p, x, y, w, h, "ARCHIVE RECEIVER  //  STATION 09", GREEN if act else tint,
               "ACTIVE" if act else "DORMANT")
        if not act:
            ui.type_lines(p, "The old receiver is dormant. It wakes only when fed all THREE tones in the right order. Tune the radio (Q) "
                             "to each band and watch the scope: every band sends a different PULSE COUNT. Dr. Wren's research notebook "
                             "explains the rule.", 99999, x + 12, y + 32, w - 24, TEXT, 7, 9)
        pulses = RECEIVER_PULSES[f]
        scol = QColor(90, 255, 150) if act else tint
        ui.scope(p, x + 12, y + 74, 250, 80, t, scol, 1.0, .04 if gp.radio_on else .5, pulses=pulses)
        ui.text(p, str(pulses), x + 272, y + 120, scol, 34, True, glow=True)
        ui.text(p, "PULSES", x + 274, y + 134, DIM, 7, True)
        ui.text(p, f"BAND {FREQS[f]} MHz  {FREQ_NAMES[f]}", x + 12, y + 168, tint, 8, True)
        if not act:
            for i in range(3):
                bx = x + 12 + i * 92
                filled = i < len(self.seq)
                c = QColor(*TINT[self.seq[i]]) if filled else QColor(60, 70, 90)
                p.fillRect(bx, y + 178, 84, 26, QColor(10, 16, 26))
                p.setPen(c)
                p.drawRect(bx, y + 178, 83, 25)
                ui.text(p, f"TONE {i + 1}", bx + 4, y + 188, DIM, 6)
                if filled:
                    ui.text(p, f"{FREQS[self.seq[i]]}", bx + 4, y + 199, c, 8, True)
            ui.text(p, f"[ENTER] send {FREQS[f]} MHz as the next tone", x + 12, y + 218, AMBER, 7, True)
            ui.text(p, "Q tune  SPACE radio  ENTER send tone  BKSP clear  ESC leave", x + 12, y + h - 7, DIM, 7)
        else:
            ui.type_lines(p, self.typer.text, self.typer.shown, x + 12, y + 190, w - 24, QColor(200, 255, 225), 8, 11)
            more = self.page + 1 < len(RECEIVER_DECODE)
            if self.typer.done and int(t * 2) % 2 == 0:
                ui.text(p, "[ENTER] next" if more else "[ESC] close", x + w - 90, y + h - 7, GREEN, 7)
        if self.msg_t > 0:
            ui.text(p, self.msg, x + w / 2, y + 232, QColor(self.msg_col.red(), self.msg_col.green(), self.msg_col.blue(),
                                                            int(255 * min(1, self.msg_t))), 8, True, True, True)
        if self.flash > 0:
            c = GREEN if act else RED
            p.fillRect(x, y, w, h, QColor(c.red(), c.green(), c.blue(), int(70 * self.flash)))
        p.restore()
