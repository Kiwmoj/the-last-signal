"""Station 09: layout, collision data and all procedural pixel art.

Static art (floor, walls, cables) is painted once into a cached QImage.
Animated art (screens, LEDs, windows, artifact) is drawn every frame by draw_prop().
Props are depth-sorted by their bottom edge so the player can walk in front of / behind them.
"""
import math
import random
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (QColor, QImage, QPainter, QPen, QPainterPath, QPolygonF,
                         QRadialGradient, QBrush, QLinearGradient)
from .story import NOTEBOOK, ECHO_PICKUP, SOURCES

WORLD_W, WORLD_H, WALL_H = 1080, 288, 66
PARTITION_X = 396   # x where the Control Room ends and the Offices & Storage begin
ANNEX_END = 640     # x where Offices & Storage end and the Research Wing begins
VAULT_END = 760     # x where the Research Wing ends and the Archive begins
ARCHIVE_END = 900   # x where the Archive ends and the Transmission Chamber begins
VAULT_FLOOR_END = 190

# Radio frequencies. Index 0 is also the world you see with the radio switched off.
ALL = frozenset((0, 1, 2))
FREQS = (88.1, 104.7, 121.3)
FREQ_NAMES = ("THE PRESENT", "THE PAST", "THE UNKNOWN")
TINT = ((255, 176, 60), (80, 230, 255), (190, 90, 255))      # amber / cyan / violet
BEAM = ((110, 150, 255), (110, 230, 255), (190, 110, 255))


def box(p, x, y, w, h, c):
    p.fillRect(int(x), int(y), int(w), int(h), QColor(*c) if isinstance(c, tuple) else c)


def lamp_flicker(t, seed=0.0):
    """Unstable power: mostly steady, with sudden brown-out dips."""
    f = .93 + .07 * math.sin(t * 9 + seed)
    if math.sin(t * 37 + seed) * math.sin(t * 23.7 + seed * 2.1) > .8:
        f *= .35
    return f


def ceiling_flicker(t, seed=0.0):
    f = lamp_flicker(t, seed)
    if math.sin(t * .6 + seed) > .96:
        f *= .15
    return f


class Prop:
    """A world object. `vis` = frequencies where it exists, `solid_in` = frequencies where it
    blocks movement, `alt` = per-frequency overrides of name/verb/lines. `hide_if`/`need`/`open_if`
    are progress flags (hidden once set / only exists once set / stops blocking once set)."""

    def __init__(self, kind, x, y, w, h, solid=True, name=None, verb="Examine",
                 lines=None, action=None, zone=None, vis=ALL, solid_in=None, alt=None,
                 hide_if=None, need=None, open_if=None, clue=None, style="plain", sid=None):
        self.kind = kind
        self.rect = QRectF(x, y, w, h)
        self.vis = frozenset(vis)
        self.solid_in = frozenset(solid_in) if solid_in is not None else (self.vis if solid else frozenset())
        self.name = name            # interactive if not None
        self.verb = verb
        self.lines = lines or []
        self.action = action
        self.alt = alt or {}
        self.clue, self.style, self.sid = clue, style, sid
        self.hide_if, self.open_if = hide_if, open_if
        self.needs = (need,) if isinstance(need, str) else tuple(need or ())
        self.zone = QRectF(*zone) if zone else self.rect.adjusted(-12, -8, 12, 18)
        self.custom_zone = zone is not None      # a hand-placed "stand here" zone beats neighbouring furniture when focusing

    def visible(self, f, flags):
        return f in self.vis and self.hide_if not in flags and all(n in flags for n in self.needs)

    def is_solid(self, f, flags):
        return self.visible(f, flags) and f in self.solid_in and self.open_if not in flags

    def spec(self, f):
        d = {"name": self.name, "verb": self.verb, "lines": self.lines, "clue": self.clue, "style": self.style}
        d.update(self.alt.get(f, {}))
        return d

    def interactive_in(self, f):
        return self.spec(f)["name"] is not None

    @property
    def sort_y(self):
        return self.rect.bottom()


class World:
    def __init__(self):
        self.spawn = (38, 192)
        self.windows = [(120, 6, 36, 28), (240, 6, 36, 28), (450, 6, 36, 28), (520, 6, 36, 28)]
        P = Prop
        self.props = [
            P("rack", 28, 22, 30, 46, name="Equipment Rack", lines=[
                "Tape reels turn slowly in the dark rack, though no tape is loaded.",
                "Each rotation leaves behind a faint whisper, like someone breathing through static."]),
            P("rack", 60, 22, 30, 46, name="Signal Rack", lines=[
                "A bank of old amplifiers. Their tubes glow a warm orange with the power off.",
                "A label reads: DO NOT TUNE BELOW 90.0. The tape is brand new."]),
            P("console", 110, 38, 100, 30, name="Main Transmitter", verb="Inspect", action="transmitter", lines=[
                "The station's main transmitter, cold and dead for years. Its fuse holder is empty.",
                "Yet the dials are warm under your fingers. Tune to 104.7 and the station remembers what it was."],
              alt={1: {"lines": [
                  "Through the radio the transmitter gleams as it once did. Fuse slot 3 is empty, and blinking.",
                  "The old log says spare fuses go missing. The Echo at the table knows where."]},
                   2: {"lines": [
                  "In the Unknown the transmitter is a throat of violet static. It whispers a coordinate you cannot hold in your head.",
                  "Something out there knows you are listening."]}}),
            P("computer", 232, 40, 48, 28, name="Terminal", verb="Use", action="terminal", lines=[
                "A station terminal. Its screen glows with a list of files."]),
            P("switch", 300, 28, 10, 14, solid=False, name="Power Switch", verb="Flip",
              action="lights", zone=(288, 40, 34, 40)),
            P("cabinet", 326, 34, 26, 34, name="Filing Cabinet", lines=[
                "Personnel files for everyone who worked at Station 09. Every drawer has been yanked open and emptied in a hurry.",
                "Only one folder is left: EVACUATION ORDER. The signature at the bottom is Dr. E. Marlowe's. The ink is smudged where his hand shook."],
              clue=("evacuated", "The station was evacuated in a hurry", "The filing cabinet was emptied in a panic. The only folder left is an evacuation order signed by Dr. Marlowe, his signature smudged.")),
            P("table", 170, 150, 84, 32, name="Logbook Table", verb="Read", style="note", lines=[
                "A weathered logbook lies open under a flickering lamp.",
                "'Night 114. The unknown band came again. It spoke Wren's name, and then it spoke ours.'",
                "The next page has been torn out. Only a faint pencil rubbing remains, too worn to read. Maybe the radio can show you what it said."],
              alt={1: {"lines": [
                  "Through the radio the torn page is whole again, the ink still wet.",
                  "'THE RESEARCH WING LOCK OPENS IN THREE TONES. FIRST, BEGIN IN MEMORY: 104.7.'"],
                       "clue": ("tone1", "Wing lock: first tone", "The research wing lock's first tone: begin in memory, 104.7 MHz.", "key")},
                   2: {"style": "voice", "lines": [
                  "The page glows with unfamiliar symbols. They form a map, and an arrow points to the south-east corner of the annex."]}}),
            P("chair", 146, 160, 16, 18, solid=False),
            P("chair", 262, 160, 16, 18, solid=False),
            P("crate", 28, 206, 30, 26, name="Supply Crate", lines=[
                "Crates stenciled STATION 09. Inside: batteries, still fully charged after all these years."]),
            P("crate", 28, 234, 30, 26, name="Supply Crate", lines=[
                "Under a tarp: a small yellow coat, and a crayon drawing of a radio tower. 'DAD'S STATION, by Nora, age 9.'",
                "Someone left in such a hurry that a child's coat stayed behind."],
              clue=("belongings", "A child's belongings", "A child's yellow coat and a crayon drawing signed 'Nora, age 9: Dad's Station' were left behind in a supply crate.")),
            P("plant", 356, 232, 16, 28, name="Dead Fern", lines=[
                "A dead fern in a cracked pot.",
                "...but a single new leaf is growing, and it glows faintly green."],
              alt={1: {"name": "Healthy Fern", "lines": ["Years ago someone watered this fern every morning. It was the operator's pride and joy."]}}),
            P("shelf", 420, 36, 70, 30, name="Dusty Shelf", lines=[
                "Spare vacuum tubes, jars of resistors, water-stained manuals.",
                "One title is circled in red ink: 'Listening Beyond the Dial'."]),
            P("crate", 560, 40, 40, 28, name="Stacked Crates", lines=[
                "Crates piled to the ceiling. One has been pried open from the inside."]),
            P("crate", 430, 222, 30, 26, name="Supply Crate", lines=[
                "Empty. Faint scratches on the inside of the lid, in groups of three."]),
            P("crate", 466, 232, 26, 22, name="Small Crate", lines=[
                "A rusted toolbox. Inside is a single sticky note: 'IT HUMS WHEN YOU ARE NEAR.'"]),
            P("artifact", 518, 140, 34, 44, name="Strange Relic", verb="Touch", lines=[
                "A relic of bent copper and glass floats a hand's width above its pedestal, humming at the same pitch as the terminal.",
                "When you lean closer, the headphones around your neck crackle to life. Something is listening back."],
              alt={1: {"name": "Empty Pedestal", "verb": "Examine", "lines": [
                  "In the past the pedestal stands empty. Whatever floats here in the present was never part of the station."]}}),
            P("door", 614, 96, 26, 64, name="Research Wing Door", verb="Inspect", action="door", open_if="door_open", lines=[
                "A heavy bulkhead door stenciled RESEARCH WING. The keypad is dark and no light answers.",
                "TONE KEY REQUIRED. The lock has no power."],
              alt={1: {"lines": [
                  "In memory a thick cable ran from the main transmitter to this lock.",
                  "The keypad has no power. Restore the transmitter and it will wake."]}}),
            # --- frequency-dependent objects ---
            P("rubble", 386, 150, 30, 46, vis=(0, 2), name="Collapsed Doorway", verb="Inspect", zone=(356, 136, 90, 76), hide_if="passage_open",
              lines=["The east corridor has collapsed. Tons of rubble choke the doorway.",
                     "Your headphones hiss strangely when you face the rubble. Somewhere on the dial, this passage still exists."],
              clue=("rubble", "The collapsed corridor", "The corridor to the Archive is blocked by rubble on 88.1 and 121.3. On 104.7 the way is clear."),
              alt={2: {"lines": ["In the Unknown the rubble is a frozen scream of stone. No less solid."]}}),
            P("arch", 386, 150, 30, 46, solid=False, vis=(1,)),
            P("echo", 140, 132, 26, 34, solid=False, vis=(1,), name="Operator's Echo", verb="Listen", style="radio", lines=[
                "A translucent operator sits at the table, scribbling, never looking up.",
                "'I hid the spare fuse where the station forgets things. Past the veil, in the south-east corner. You will need to listen on 121.3.'"],
              clue=("echo_fuse", "The hidden fuse", "The Operator's Echo hid a spare fuse past a veil in the south-east corner of the annex. It can only be reached on 121.3.")),
            P("veil", 556, 206, 70, 8, solid_in=(0, 1)),
            P("veil", 556, 206, 12, 68, solid_in=(0, 1)),
            P("fuse", 586, 244, 12, 12, solid=False, vis=(2,), hide_if="fuse_taken", name="Spare Fuse", verb="Take",
              action="fuse_take", lines=["A glowing fuse, cold as ice. It hums in your palm like a trapped insect."]),
            P("glyphs", 500, 20, 46, 40, solid=False, vis=(2,), name="Wall Glyphs", verb="Read", zone=(486, 20, 74, 70), style="voice",
              lines=["Violet symbols crawl across the wall. A hand-drawn arrow points toward the south-east corner.",
                     "'WHAT THE STATION FORGOT IS KEPT BEHIND THE VEIL.'"],
              clue=("glyph_arrow", "Wall glyphs", "Violet glyphs point to the south-east corner of the annex: 'what the station forgot is kept behind the veil.'")),
            P("sigil", 572, 148, 30, 30, solid=False, vis=(2,), name="Floor Sigil", verb="Read", style="voice",
              lines=["A sigil glows on the floor, three marks around a circle.",
                     "'SECOND, LISTEN TO THE DARK: 121.3. THE DARK REMEMBERS WHAT YOU CANNOT.'"],
              clue=("tone2", "Wing lock: second tone", "The research wing lock's second tone: listen to the dark, 121.3 MHz.", "key")),
            P("plaque", 592, 108, 14, 14, solid=False, vis=(0,), name="Brass Plaque", verb="Read", zone=(578, 98, 40, 40), style="note",
              lines=["A brass plaque beside the door, green with age.",
                     "'THIRD, THE PRESENT. SPEAK WITH YOUR OWN VOICE: 88.1.'"],
              clue=("tone3", "Wing lock: third tone", "The research wing lock's third tone: the present, 88.1 MHz. This plaque only exists on 88.1.", "key")),
            # --- Research Wing ---
            P("beacon", 668, 96, 40, 60, name="Experiment Array", verb="Examine", action="beacon", lines=[
                "EXPERIMENT ARRAY. Channel one: THE PRESENT. A steady carrier at 88.1, exactly what the station says it should be."],
              alt={1: {"lines": ["Channel two: THE PAST. The array replays echoes of moments that already happened. A man's voice, patient: 'Test seven. Subject: yesterday.'"]},
                   2: {"lines": ["Channel three, unlabelled. The array reaches for a moment nobody has lived, or perhaps one nobody should. The display repeats a single word: LISTENING."]}}),
            P("mural", 650, 20, 88, 40, solid=False, name="Crew Photograph", verb="Study", zone=(646, 20, 96, 66), lines=[
                "A faded crew photograph: nine researchers on the station steps. One of them is a girl in a yellow coat."],
              alt={1: {"lines": ["The photograph is sharp again: Dr. Marlowe in the middle, a girl in a yellow coat on his shoulders, and Wren beside him, not smiling."],
                       "clue": ("crew_photo", "The crew photograph", "A photograph of the Station 09 crew: Dr. Marlowe, Dr. Wren and a girl in a yellow coat, Nora.")},
                   2: {"lines": ["The photograph is a star chart. One star pulses, a place that does not exist. It matches the array."]}}),
            # --- Stage 4: interactive objects ---
            P("oldradio", 300, 108, 32, 30, name="Old Radio", verb="Listen to", action="oldradio", style="radio", lines=[
                "A wooden tabletop radio from another era. Its dial glass is cracked and nothing answers when you turn the knob.",
                "A cable runs from the back toward the main transmitter. It looks like it needs the transmitter's power."]),
            P("notebook", 318, 192, 56, 30, name="Research Notebook", verb="Read", style="note", zone=(306, 182, 80, 56),
              lines=list(NOTEBOOK[0][0]), clue=NOTEBOOK[0][1],
              alt={1: {"lines": list(NOTEBOOK[1][0]), "clue": NOTEBOOK[1][1]},
                   2: {"lines": list(NOTEBOOK[2][0]), "clue": NOTEBOOK[2][1], "style": "voice"}}),
            P("secdoor", 734, 96, 26, 64, name="Archive Door", verb="Use", action="secdoor", open_if="archive_open", lines=[
                "A steel door marked ARCHIVE, with a handwritten note taped on: DO NOT OPEN. A keypad waits for a passphrase."]),
            P("archive", 768, 34, 48, 34, name="Archive Shelves", verb="Examine", lines=[
                "Shelves of reel boxes and ledgers. Every label has been scratched out except one, repeated on dozens of boxes: 09-A."]),
            P("archive", 832, 34, 48, 34, name="Archive Shelves", verb="Examine", lines=[
                "Decades of recordings, all dated 03:33 AM."]),
            P("receiver", 800, 84, 52, 60, name="Transmission Receiver", verb="Operate", action="receiver", style="radio", lines=[
                "An enormous old receiver, all dials and coils."]),
            # --- Echo Receiver: the handheld on the side table, and the hidden signals only it can find ---
            # --- Staff Locker 2-A: a four-digit code whose digits are left in three different rooms ---
            P("board", 262, 196, 30, 38, name="Duty Board", verb="Read", style="note", lines=[
                "A cork board of shift rotas. One card is pinned apart from the rest: 'LOCKER 2-A, in the Offices. Four digits, one per note. "
                "The notes are in Control, in the Offices and in the Wing, and each reads clearly on only one frequency.'"],
              clue=("lk_rule", "Locker 2-A: how it works", "Staff Locker 2-A (Offices) takes four digits. They are on the Control Room duty board, the Offices whiteboard and the Research Wing slate. Each note only reads clearly on one frequency.", "key"),
              alt={1: {"style": "voice", "lines": ["In the Past the board is crowded with cards, and one line is in Elias's handwriting: 'Locker 2-A. My digit: 6. First.'"],
                       "clue": ("lk_1", "Locker digit 1: 6", "Control Room duty board, 104.7 MHz: Elias wrote 'Locker 2-A. My digit: 6. First.'", "key")},
                   2: {"style": "voice", "lines": ["The cards are blank rectangles of violet light. Nothing to read here."], "clue": None}}),
            P("board", 426, 118, 30, 34, name="Maintenance Whiteboard", verb="Read", style="note", lines=[
                "A whiteboard of repair jobs. Circled in red: 'LOCKER 2-A, second digit: 4. Tell Wren.'"],
              clue=("lk_2", "Locker digit 2: 4", "Offices whiteboard, 88.1 MHz: 'LOCKER 2-A, second digit: 4. Tell Wren.'", "key"),
              alt={1: {"lines": ["On this side of time the board has just been wiped clean."], "clue": None},
                   2: {"style": "voice", "lines": ["Under the violet glow the eraser smears resolve into a single drawn circle, and beneath it: 'third digit: 0. An empty circle.'"],
                       "clue": ("lk_3", "Locker digit 3: 0", "Offices whiteboard, 121.3 MHz: 'third digit: 0.' An empty circle.", "key")}}),
            P("board", 648, 162, 24, 26, name="Technician's Slate", verb="Read", style="note", lines=[
                "A chalk slate on a little easel: 'Locker 2-A, last digit: 2. Don't tell Elias.'"],
              clue=("lk_4", "Locker digit 4: 2", "Research Wing slate, 88.1 MHz: 'Locker 2-A, last digit: 2. Don't tell Elias.'", "key"),
              alt={1: {"lines": ["The slate is clean on this side of time."], "clue": None},
                   2: {"style": "voice", "lines": ["Violet dust drifts across the slate. The writing is unreadable here. The Present shows it clearly."], "clue": None}}),
            P("locker", 504, 226, 26, 40, name="Staff Locker 2-A", verb="Open", action="locker", lines=[
                "A grey steel locker stencilled 2-A. A four-digit dial lock hangs from the latch."]),
            P("safe", 714, 160, 22, 28, name="Wing Safe", verb="Open", action="safe", lines=[
                "A small wall safe on a trolley, three dials. A child's handwriting is scratched into the door: 'Count what Nora drew.'"],
              clue=("sf_rule", "Wing Safe: count what Nora drew", "The Wing Safe takes three digits. Nora drew in three rooms: the Control Room, the Offices and the Archive. Count what is in each drawing. Each shows clearly on only one frequency.", "key")),
            P("board", 84, 214, 24, 30, name="Child's Drawing", verb="Look at", style="note",
              lines=["A sheet of grey paper pinned above the transmitter. On this side of time it is smudged beyond reading."],
              alt={1: {"style": "voice", "lines": ["A child's crayon drawing: a smiling sun with NINE rays. 'for daddy - nora'."],
                       "clue": ("sf_1", "Safe digit 1: 9", "Control Room drawing, 104.7 MHz: a sun with nine rays, signed 'for daddy - nora'.", "key")}}),
            P("drawing", 548, 24, 16, 20, solid=False, name="Child's Drawing", verb="Look at", zone=(534, 62, 44, 50), style="note",
              lines=["A child's crayon drawing: a single big tree with a yellow door in its trunk. 'our tree'."],
              clue=("sf_2", "Safe digit 2: 1", "Offices drawing, 88.1 MHz: one big tree. 'our tree'.", "key"),
              alt={1: {"lines": ["On this side of time the paper is blank."], "clue": None},
                   2: {"style": "voice", "lines": ["The paper is a square of violet light. The picture is unreadable here. The Present shows it clearly."], "clue": None}}),
            P("drawing", 846, 14, 16, 20, solid=False, name="Child's Drawing", verb="Look at", zone=(850, 66, 36, 40), style="note",
              lines=["A sheet of grey paper pinned to the shelves. It is smudged beyond reading on this side of time."],
              alt={2: {"style": "voice", "lines": ["A child's crayon drawing of the night sky: SEVEN stars and a tiny radio tower. 'listen'."],
                       "clue": ("sf_3", "Safe digit 3: 7", "Archive drawing, 121.3 MHz: seven stars over a little radio tower. 'listen'.", "key")}}),
            P("sidetable", 66, 140, 46, 22, name=None),
            P("echorecv", 82, 134, 14, 30, solid=False, name="Echo Receiver", verb="Pick up", action="echo_pickup",
              hide_if="echo_found", zone=(60, 120, 60, 60), lines=list(ECHO_PICKUP)),
            P("source", 352, 118, 24, 24, solid=False, vis=(1,), need="echo_track", hide_if="src_tut", name=SOURCES["tut"][0],
              verb="Lock onto", action="source", sid="tut", style="radio", zone=(340, 106, 48, 48), lines=SOURCES["tut"][1], clue=SOURCES["tut"][2]),
            P("source", 468, 118, 24, 24, solid=False, vis=(2,), need="echo_track", hide_if="src_wren", name=SOURCES["wren"][0],
              verb="Lock onto", action="source", sid="wren", style="voice", zone=(456, 106, 48, 48), lines=SOURCES["wren"][1], clue=SOURCES["wren"][2]),
            P("source", 652, 150, 24, 24, solid=False, vis=(1,), need="echo_track", hide_if="src_nora", name=SOURCES["nora"][0],
              verb="Lock onto", action="source", sid="nora", style="radio", zone=(640, 138, 48, 48), lines=SOURCES["nora"][1], clue=SOURCES["nora"][2]),
            P("source", 854, 138, 24, 24, solid=False, vis=(2,), need=("echo_track", "p3_done"), hide_if="src_final", name=SOURCES["final"][0],
              verb="Lock onto", action="source", sid="final", style="voice", zone=(842, 126, 48, 48), lines=SOURCES["final"][1], clue=SOURCES["final"][2]),
            # --- Story sources: Elias's recording and the echo trail ---
            P("source", 118, 98, 24, 24, solid=False, vis=(2,), need=("echo_track", "fixed"), hide_if="src_elias", name=SOURCES["elias"][0],
              verb="Lock onto", action="source", sid="elias", style="voice", zone=(106, 86, 48, 48), lines=SOURCES["elias"][1], clue=SOURCES["elias"][2]),
            P("source", 100, 170, 24, 24, solid=False, vis=(1,), need=("echo_track", "ch4"), hide_if="src_trail1", name=SOURCES["trail1"][0],
              verb="Lock onto", action="source", sid="trail1", style="radio", zone=(88, 158, 48, 48), lines=SOURCES["trail1"][1], clue=SOURCES["trail1"][2]),
            P("source", 440, 170, 24, 24, solid=False, vis=(2,), need=("echo_track", "src_trail1"), hide_if="src_trail2", name=SOURCES["trail2"][0],
              verb="Lock onto", action="source", sid="trail2", style="voice", zone=(428, 158, 48, 48), lines=SOURCES["trail2"][1], clue=SOURCES["trail2"][2]),
            P("source", 712, 150, 22, 22, solid=False, vis=(0,), need=("echo_track", "src_trail2"), hide_if="src_trail3", name=SOURCES["trail3"][0],
              verb="Lock onto", action="source", sid="trail3", style="radio", zone=(700, 138, 48, 48), lines=SOURCES["trail3"][1], clue=SOURCES["trail3"][2]),
            # --- Chapter 4: the archive rack that reveals who the signal is ---
            P("rack09", 790, 162, 40, 24, need="src_trail3", name="Recording Rack 09-A", verb="Play", action="rack", style="terminal", lines=[
                "A rack of reels. One is labelled 09-A, and it is warm, as if someone has just played it.",
                "Your own initials are on the label."]),
            # --- Chapter 5: the date plaques, the chamber door, and the Transmission Chamber ---
            P("datepanel", 360, 28, 22, 28, solid=False, vis=(0,), need="ch4_done", name="Wall Calendar", verb="Read", style="note", zone=(346, 24, 50, 60),
              lines=["A wall calendar that was not here before, stopped on one day: the 14th, circled in red."],
              clue=("date_day", "Incident date: the day", "A wall calendar in the control room (88.1) is stopped on the 14th, circled in red.", "key")),
            P("datepanel", 506, 26, 22, 28, solid=False, vis=(1,), need="ch4_done", name="Office Calendar", verb="Read", style="note", zone=(492, 22, 50, 60),
              lines=["A faded office calendar from the past: AUGUST. The same day is circled."],
              clue=("date_month", "Incident date: the month", "A calendar in the offices (104.7) shows AUGUST, 08, with the same day circled.", "key")),
            P("datepanel", 668, 168, 22, 22, solid=False, vis=(2,), need="ch4_done", name="Glowing Digits", verb="Read", style="voice", zone=(654, 156, 50, 40),
              lines=["Violet digits glow on the floor of the research wing: 80."],
              clue=("date_year", "Incident date: the year", "Glowing digits in the research wing (121.3) read 80: the year 1980.", "key")),
            P("chamberdoor", 874, 96, 26, 64, name="Chamber Door", verb="Use", action="chamberdoor", open_if="chamber_open", lines=[
                "A massive door stenciled TRANSMISSION CHAMBER. A keypad waits for a date: day, month, year."]),
            P("chterm", 922, 40, 48, 28, name="Research Terminal", verb="Use", action="terminal2", lines=[
                "Elias's own terminal. Its screen glows with his final files."]),
            P("finaltx", 976, 84, 72, 62, name="Final Transmitter", verb="Operate", action="finaltx", style="radio", lines=[
                "THE FINAL TRANSMITTER. A tower of coils and dials, humming at a pitch that matches your pulse."]),
            P("lectern", 934, 150, 28, 24, name="Elias's Final Notes", verb="Read", style="note",
              lines=["Elias's last notes. 'To send the message, the transmitter must hear each layer in turn.'"],
              alt={2: {"style": "voice", "lines": ["'Begin with the unknown. It must hear you first.'"],
                       "clue": ("final_1", "Final transmission: first", "Elias's notes (121.3): begin the final transmission with the unknown. It must hear you first.", "key")},
                   0: {"lines": ["'Then the present. It carries the words.'"],
                       "clue": ("final_2", "Final transmission: second", "Elias's notes (88.1): then the present. It carries the words.", "key")},
                   1: {"lines": ["'End with the past. It must remember them.'"],
                       "clue": ("final_3", "Final transmission: third", "Elias's notes (104.7): end with the past. It must remember the words.", "key")}}),
        ]
        self.walls = [
            QRectF(0, 0, WORLD_W, WALL_H),
            QRectF(0, 0, 14, WORLD_H),
            QRectF(0, 274, ANNEX_END, 14),
            QRectF(ANNEX_END - 14, WALL_H, 14, 30),          # annex east wall, above the door gap
            QRectF(ANNEX_END - 14, 160, 14, 114),            # ... and below it
            QRectF(ANNEX_END, VAULT_FLOOR_END, WORLD_W - ANNEX_END, WORLD_H - VAULT_FLOOR_END),
            QRectF(WORLD_W - 14, 0, 14, WORLD_H),
            QRectF(VAULT_END - 14, WALL_H, 14, 30),          # research wing east wall, above the Archive door gap
            QRectF(VAULT_END - 14, 160, 14, VAULT_FLOOR_END - 160),
            QRectF(ARCHIVE_END - 14, WALL_H, 14, 30),        # Archive east wall, above the chamber door gap
            QRectF(ARCHIVE_END - 14, 160, 14, VAULT_FLOOR_END - 160),
            QRectF(PARTITION_X, WALL_H, 12, 84),
            QRectF(PARTITION_X, 196, 12, 78),
        ]
        # Hidden things the radio / Echo Receiver can detect: (band, x, y, flag that retires it[, flag it needs])
        self.hotspots = [
            (0, 599, 116, None), (0, 160, 70, "fixed"), (0, 316, 126, "p1_done"), (0, 346, 206, None),
            (1, 401, 172, None), (1, 154, 166, "fixed"), (1, 160, 66, "fixed"), (1, 316, 126, "p1_done"),
            (2, 592, 248, "fuse_taken"), (2, 523, 56, None), (2, 587, 166, None), (2, 688, 130, None),
            (2, 316, 126, "p1_done"), (2, 346, 206, None), (0, 826, 116, "p3_done"), (1, 826, 116, "p3_done"),
            (2, 826, 116, "p3_done"),
            (0, 371, 42, "chamber_open", "ch4_done"), (1, 517, 40, "chamber_open", "ch4_done"), (2, 679, 179, "chamber_open", "ch4_done"),
            (1, 277, 215, "clue_lk_1"), (0, 441, 135, "clue_lk_2"), (2, 441, 135, "clue_lk_3"), (0, 660, 176, "clue_lk_4"),
            (1, 96, 229, "clue_sf_1"), (0, 556, 34, "clue_sf_2"), (2, 854, 24, "clue_sf_3"),
            (0, 948, 162, "final_ready", "chamber_open"), (1, 948, 162, "final_ready", "chamber_open"), (2, 948, 162, "final_ready", "chamber_open"),
        ]
        self.bg = build_background(self.windows)
        self.overlays = {1: build_overlay(1), 2: build_overlay(2)}

    def solids_for(self, f, flags):
        """Collision rectangles as they exist on frequency f with the given progress flags."""
        return self.walls + [pr.rect for pr in self.props if pr.is_solid(f, flags)]

    @staticmethod
    def zone_name(x):
        if x < PARTITION_X:
            return "CONTROL ROOM"
        if x < ANNEX_END:
            return "OFFICES & STORAGE"
        if x < VAULT_END:
            return "RESEARCH WING"
        return "THE ARCHIVE" if x < ARCHIVE_END else "TRANSMISSION CHAMBER"


# --------------------------------------------------------------------------- static art
def build_background(windows):
    img = QImage(WORLD_W, WORLD_H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    rnd = random.Random(3)
    # floor: checkered tiles in the control room, plain concrete in the annex
    for ty in range(WALL_H, WORLD_H, 16):
        for tx in range(0, WORLD_W, 16):
            if tx >= ANNEX_END and ty >= VAULT_FLOOR_END:
                continue
            n = rnd.randint(-3, 3)
            if tx >= ARCHIVE_END:
                b = (30, 28, 44)
            elif tx >= VAULT_END:
                b = (38, 30, 44)
            elif tx >= ANNEX_END:
                b = (26, 36, 46)
            elif tx >= 400:
                b = (38, 40, 46)
            else:
                b = (30, 34, 48) if (tx // 16 + ty // 16) % 2 == 0 else (35, 39, 56)
            box(p, tx, ty, 16, 16, (b[0] + n, b[1] + n, b[2] + n))
            box(p, tx, ty, 16, 1, (17, 19, 27))
            box(p, tx, ty, 1, 16, (17, 19, 27))
            if rnd.random() < .12:
                box(p, tx + rnd.randint(2, 9), ty + rnd.randint(2, 12), rnd.randint(2, 6), 1, (48, 52, 70))
    p.setPen(Qt.PenStyle.NoPen)
    for _ in range(16):
        p.setBrush(QColor(8, 8, 12, 55))
        p.drawEllipse(QPointF(rnd.randint(20, 620), rnd.randint(80, 268)), rnd.randint(5, 16), rnd.randint(3, 8))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QColor(12, 14, 20))
    for _ in range(7):
        x, y = rnd.randint(30, 600), rnd.randint(80, 260)
        for _ in range(4):
            nx, ny = x + rnd.randint(-8, 8), y + rnd.randint(2, 7)
            p.drawLine(x, y, nx, ny)
            x, y = nx, ny
    # rug under the logbook table
    box(p, 136, 126, 158, 86, (66, 24, 32))
    box(p, 140, 130, 150, 78, (86, 34, 42))
    box(p, 144, 134, 142, 70, (60, 22, 30))
    for i in range(7):
        for j in range(3):
            cx, cy = 156 + i * 20, 146 + j * 20
            p.setBrush(QColor(120, 70, 60))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(QPolygonF([QPointF(cx, cy - 4), QPointF(cx + 4, cy), QPointF(cx, cy + 4), QPointF(cx - 4, cy)]))
    for x in range(138, 294, 4):
        box(p, x, 123, 1, 3, (150, 130, 110))
        box(p, x, 212, 1, 3, (150, 130, 110))

    # back wall
    g = QLinearGradient(0, 0, 0, WALL_H)
    g.setColorAt(0, QColor(14, 18, 28))
    g.setColorAt(1, QColor(32, 38, 54))
    p.fillRect(0, 0, WORLD_W, WALL_H, QBrush(g))
    for x in range(0, WORLD_W, 40):
        box(p, x, 0, 1, WALL_H, (10, 13, 20))
        box(p, x + 1, 0, 1, WALL_H, (40, 48, 66))
    for _ in range(160):
        box(p, rnd.randint(0, WORLD_W), rnd.randint(0, 44), rnd.randint(2, 5), 1, (255, 255, 255, 12))
    box(p, 0, 44, WORLD_W, 22, (22, 27, 38))
    box(p, 0, 44, WORLD_W, 1, (72, 84, 108))
    box(p, 0, 45, WORLD_W, 1, (10, 12, 18))
    box(p, 0, 62, WORLD_W, 4, (10, 12, 18))
    box(p, 0, 62, WORLD_W, 1, (52, 60, 78))
    # ceiling pipes + brackets
    box(p, 0, 3, WORLD_W, 4, (40, 46, 58)); box(p, 0, 3, WORLD_W, 1, (92, 102, 124))
    box(p, 0, 10, WORLD_W, 3, (70, 44, 34)); box(p, 0, 10, WORLD_W, 1, (120, 78, 58))
    for x in range(20, WORLD_W, 60):
        box(p, x, 2, 3, 12, (20, 24, 32))
    # hanging cables
    p.setBrush(Qt.BrushStyle.NoBrush)
    for x0, sag in ((96, 22), (298, 28), (420, 20), (600, 24)):
        path = QPainterPath(QPointF(x0, 13))
        path.cubicTo(x0 + 6, 13 + sag, x0 + 22, 13 + sag, x0 + 28, 13)
        p.setPen(QPen(QColor(8, 9, 12), 2)); p.drawPath(path)
        p.setPen(QPen(QColor(44, 50, 68), 1)); p.drawPath(path.translated(0, -1))
    # windows (frames; the animated sky is drawn per frame)
    for (wx, wy, w, h) in windows:
        box(p, wx - 3, wy - 3, w + 6, h + 6, (8, 10, 16))
        box(p, wx - 3, wy - 3, w + 6, 1, (60, 70, 92))
        box(p, wx - 5, wy + h + 3, w + 10, 3, (74, 82, 100))
        box(p, wx - 5, wy + h + 6, w + 10, 1, (10, 12, 18))
    # map poster: a place that does not exist
    box(p, 172, 12, 44, 24, (150, 140, 106)); box(p, 172, 12, 44, 1, (190, 180, 140))
    p.setPen(QColor(100, 90, 70))
    for i in range(5):
        p.drawLine(176 + i * 3, 30, 180 + i * 6, 16 + i % 3 * 4)
    p.setPen(QPen(QColor(200, 40, 40), 2))
    p.drawLine(200, 18, 208, 28); p.drawLine(208, 18, 200, 28)
    # stopped clock at 3:33
    p.setPen(QPen(QColor(10, 12, 16), 2)); p.setBrush(QColor(200, 198, 185))
    p.drawEllipse(QPointF(339, 18), 8, 8)
    p.setPen(QColor(20, 20, 24))
    p.drawLine(339, 18, 339, 12); p.drawLine(339, 18, 344, 21)
    # hazard sign in the annex
    box(p, 600, 14, 22, 16, (220, 180, 40)); box(p, 600, 14, 22, 1, (10, 10, 10)); box(p, 600, 29, 22, 1, (10, 10, 10))
    box(p, 610, 18, 2, 7, (20, 20, 20)); box(p, 610, 27, 2, 1, (20, 20, 20))

    # side and bottom walls
    for (x, y, w, h) in ((0, 0, 14, WORLD_H), (0, 274, ANNEX_END, 14),
                         (ANNEX_END - 14, WALL_H, 14, 30), (ANNEX_END - 14, 160, 14, 114),
                         (ANNEX_END, VAULT_FLOOR_END, WORLD_W - ANNEX_END, 14), (WORLD_W - 14, 0, 14, VAULT_FLOOR_END + 14),
                         (VAULT_END - 14, WALL_H, 14, 30), (VAULT_END - 14, 160, 14, VAULT_FLOOR_END - 160),
                         (ARCHIVE_END - 14, WALL_H, 14, 30), (ARCHIVE_END - 14, 160, 14, VAULT_FLOOR_END - 160)):
        box(p, x, y, w, h, (13, 16, 24))
        box(p, x, y, 1, h, (62, 72, 94))
    box(p, 14, 274, ANNEX_END - 28, 1, (62, 72, 94))
    # partition wall with hazard-striped doorway posts
    for (y, h) in ((WALL_H, 84), (196, 78)):
        box(p, PARTITION_X, y, 12, h, (34, 40, 56))
        box(p, PARTITION_X, y, 2, h, (74, 86, 112))
        box(p, PARTITION_X + 10, y, 2, h, (14, 16, 24))
    for y0 in (144, 196):
        for i in range(0, 12, 4):
            box(p, PARTITION_X + i, y0, 2, 6, (230, 190, 40))
            box(p, PARTITION_X + i + 2, y0, 2, 6, (20, 20, 24))
    # floor cables snaking between machines
    p.setBrush(Qt.BrushStyle.NoBrush)
    for pts in (((43, 68), (60, 96), (96, 88), (124, 68)),
                ((74, 68), (90, 108), (190, 104), (215, 68)),
                ((190, 68), (214, 92), (240, 84), (250, 68)),
                ((250, 68), (300, 100), (330, 92), (338, 68)),
                ((440, 66), (470, 120), (500, 150), (520, 176))):
        path = QPainterPath(QPointF(*pts[0]))
        path.cubicTo(QPointF(*pts[1]), QPointF(*pts[2]), QPointF(*pts[3]))
        p.setPen(QPen(QColor(8, 9, 12), 3)); p.drawPath(path)
        p.setPen(QPen(QColor(40, 46, 64), 1)); p.drawPath(path.translated(0, -1))
    # Signal Vault: ring platform under the beacon and heavy conduits on the wall
    p.setBrush(Qt.BrushStyle.NoBrush)
    for rr, col in ((46, (28, 60, 70)), (36, (44, 96, 108)), (26, (28, 60, 70))):
        p.setPen(QPen(QColor(*col), 2))
        p.drawEllipse(QPointF(688, 150), rr, rr * .55)
    p.setPen(QPen(QColor(44, 96, 108), 1))
    for a in range(0, 360, 30):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        p.drawLine(QPointF(688 + ca * 26, 150 + sa * 14), QPointF(688 + ca * 46, 150 + sa * 25))
    for yy, c in ((6, (40, 46, 58)), (14, (70, 44, 34))):
        box(p, ANNEX_END, yy, WORLD_W - ANNEX_END, 3, c)
    for x in range(660, 740, 28):
        box(p, x, 2, 3, 14, (20, 24, 32))
    # Archive: worn rug in front of the receiver, tall shelving rails on the wall
    box(p, 782, 100, 106, 70, (52, 22, 34)); box(p, 786, 104, 98, 62, (70, 30, 44)); box(p, 790, 108, 90, 54, (48, 20, 30))
    for x in range(784, 886, 4):
        box(p, x, 97, 1, 3, (150, 130, 110)); box(p, x, 170, 1, 3, (150, 130, 110))
    # Transmission Chamber: a ring platform under the final transmitter, conduits and cables
    p.setBrush(Qt.BrushStyle.NoBrush)
    for rr, col in ((62, (36, 34, 64)), (48, (60, 56, 112)), (34, (36, 34, 64))):
        p.setPen(QPen(QColor(*col), 2))
        p.drawEllipse(QPointF(1012, 150), rr, rr * .5)
    p.setPen(QPen(QColor(60, 56, 112), 1))
    for a in range(0, 360, 24):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        p.drawLine(QPointF(1012 + ca * 34, 150 + sa * 17), QPointF(1012 + ca * 62, 150 + sa * 31))
    for yy, c in ((8, (40, 40, 60)), (16, (70, 44, 34))):
        box(p, ARCHIVE_END, yy, WORLD_W - ARCHIVE_END, 3, c)
    for x in range(920, 1060, 30):
        box(p, x, 2, 3, 16, (20, 22, 34))
    # the station's entrance on the west wall: the door Alex came through
    box(p, 0, 156, 14, 50, (30, 22, 18)); box(p, 0, 156, 3, 50, (120, 84, 56)); box(p, 11, 156, 3, 50, (12, 10, 10))
    box(p, 3, 160, 8, 42, (52, 36, 26)); box(p, 8, 180, 2, 3, (200, 180, 90))
    p.end()
    return img


def _glyph(p, x, y, seed, col):
    r = random.Random(seed)
    p.setPen(QPen(col, 1))
    pts = [(x + r.randint(0, 8), y + r.randint(0, 10)) for _ in range(r.randint(3, 5))]
    for a, b in zip(pts, pts[1:]):
        p.drawLine(a[0], a[1], b[0], b[1])
    if r.random() < .5:
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(x + 4, y + 5), 5, 5)


def build_overlay(f):
    """Extra static art painted over the base level while tuned to frequency f (1 or 2)."""
    img = QImage(WORLD_W, WORLD_H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    rnd = random.Random(40 + f)
    if f == 1:
        # the station as a clean blueprint, with the corridor threshold restored
        p.setPen(QColor(80, 230, 255, 22))
        for x in range(0, ANNEX_END, 32):
            p.drawLine(x, WALL_H, x, 274)
        for y in range(WALL_H, 274, 32):
            p.drawLine(14, y, ANNEX_END - 14, y)
        box(p, 388, 150, 26, 46, (90, 170, 190, 60))
        for i in range(0, 46, 8):
            box(p, 398, 152 + i, 6, 2, (150, 240, 255, 120))
    else:
        col = QColor(190, 90, 255, 150)
        for i in range(44):
            _glyph(p, rnd.randint(20, 740), rnd.randint(16, 54), i, QColor(190, 90, 255, rnd.randint(70, 140)))
        for i in range(26):
            _glyph(p, rnd.randint(30, 600), rnd.randint(80, 262), 100 + i, QColor(190, 90, 255, rnd.randint(40, 90)))
        for _ in range(9):
            x, y = rnd.randint(30, 600), rnd.randint(80, 260)
            pts = [QPointF(x, y)]
            for _ in range(5):
                x += rnd.randint(-10, 10)
                y += rnd.randint(3, 10)
                pts.append(QPointF(x, y))
            path = QPainterPath(pts[0])
            for q in pts[1:]:
                path.lineTo(q)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(190, 90, 255, 50), 3)); p.drawPath(path)
            p.setPen(QPen(QColor(230, 160, 255, 170), 1)); p.drawPath(path)
        # chevrons on the floor leading toward the veil alcove
        p.setPen(QPen(QColor(220, 130, 255, 170), 1))
        for i in range(6):
            cx, cy = 440 + i * 21, 196 + i * 8
            p.drawLine(cx - 4, cy - 3, cx, cy); p.drawLine(cx, cy, cx - 4, cy + 3)
    p.end()
    return img


# --------------------------------------------------------------------------- animated art
def _windows_present(p, world, t, flash):
    for i, (wx, wy, w, h) in enumerate(world.windows):
        r = QRectF(wx, wy, w, h)
        g = QLinearGradient(wx, wy, wx, wy + h)
        g.setColorAt(0, QColor(5, 9, 22))
        g.setColorAt(1, QColor(18, 26, 50))
        p.fillRect(r, QBrush(g))
        p.save()
        p.setClipRect(r)
        if i == 0:
            rg = QRadialGradient(wx + 26, wy + 9, 12)
            rg.setColorAt(0, QColor(200, 215, 240, 150)); rg.setColorAt(1, QColor(200, 215, 240, 0))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(rg)); p.drawEllipse(QPointF(wx + 26, wy + 9), 12, 12)
            p.setBrush(QColor(214, 224, 240)); p.drawEllipse(QPointF(wx + 26, wy + 9), 5, 5)
        if i == 3:
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(4, 6, 12))
            p.drawPolygon(QPolygonF([QPointF(wx + 8, wy + h), QPointF(wx + 18, wy + h), QPointF(wx + 13, wy + 4)]))
            if (t % 1.4) < .5:
                box(p, wx + 12, wy + 3, 2, 2, (255, 60, 60))
        p.setPen(QColor(150, 180, 230, 90))
        for k in range(12):
            rx = wx + (k * 37 + i * 11) % w
            ry = wy + ((t * 110 + k * 29) % (h + 8)) - 4
            p.drawLine(int(rx), int(ry), int(rx - 1), int(ry + 4))
        if flash > 0:
            p.fillRect(r, QColor(200, 215, 255, int(210 * flash)))
        p.restore()
        box(p, wx + w // 2 - 1, wy, 2, h, (9, 11, 17))
        box(p, wx, wy + h // 2 - 1, w, 2, (9, 11, 17))


def draw_windows(p, world, t, flash, f=0):
    """Windows show a different sky per frequency: stormy night / bright dusk / a watching eye."""
    if f == 0:
        return _windows_present(p, world, t, flash)
    for i, (wx, wy, w, h) in enumerate(world.windows):
        r = QRectF(wx, wy, w, h)
        g = QLinearGradient(wx, wy, wx, wy + h)
        if f == 1:
            g.setColorAt(0, QColor(30, 90, 130)); g.setColorAt(1, QColor(170, 225, 235))
        else:
            g.setColorAt(0, QColor(40, 0, 70)); g.setColorAt(1, QColor(150, 30, 140))
        p.fillRect(r, QBrush(g))
        p.save()
        p.setClipRect(r)
        p.setPen(Qt.PenStyle.NoPen)
        if f == 1:
            p.setBrush(QColor(255, 240, 200, 235)); p.drawEllipse(QPointF(wx + w * .7, wy + h * .6), 5, 5)
            for k in range(2):
                cx = wx + ((t * 6 + k * 20 + i * 9) % (w + 20)) - 10
                p.setBrush(QColor(255, 255, 255, 70)); p.drawEllipse(QPointF(cx, wy + 6 + k * 8), 9, 3)
            if i == 3:
                p.setBrush(QColor(8, 24, 34))
                p.drawPolygon(QPolygonF([QPointF(wx + 8, wy + h), QPointF(wx + 18, wy + h), QPointF(wx + 13, wy + 4)]))
        else:
            ex, ey = wx + w / 2, wy + h / 2
            p.setBrush(QColor(235, 200, 255, 210)); p.drawEllipse(QPointF(ex, ey), 13, 8)
            p.setBrush(QColor(30, 0, 40)); p.drawEllipse(QPointF(ex + math.sin(t * .9 + i) * 4, ey), 3, 7)
            p.setPen(QColor(220, 130, 255, 90))
            for k in range(8):
                rx = wx + (k * 31 + i * 7) % w
                p.drawLine(int(rx), int(wy + ((t * 40 + k * 17) % h)), int(rx), int(wy + ((t * 40 + k * 17) % h) + 3))
        p.restore()
        box(p, wx + w // 2 - 1, wy, 2, h, (9, 11, 17))
        box(p, wx, wy + h // 2 - 1, w, 2, (9, 11, 17))


def draw_beams(p, world, t, flash, f=0):
    """Additive moonlight shafts falling from the windows onto the floor."""
    p.setPen(Qt.PenStyle.NoPen)
    for (wx, wy, w, h) in world.windows:
        g = QLinearGradient(0, WALL_H, 0, WALL_H + 90)
        a = int((26 + 6 * math.sin(t * .7 + wx)) + 160 * flash)
        c = BEAM[f]
        g.setColorAt(0, QColor(c[0], c[1], c[2], min(255, a)))
        g.setColorAt(1, QColor(c[0], c[1], c[2], 0))
        p.setBrush(QBrush(g))
        p.drawPolygon(QPolygonF([QPointF(wx, WALL_H), QPointF(wx + w, WALL_H),
                                 QPointF(wx + w + 30, WALL_H + 90), QPointF(wx + 30, WALL_H + 90)]))


def _console(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    alive = "fixed" in st.flags or st.vf != 0      # dead in the present until repaired
    box(p, x, y, w, h, (30, 38, 54)); box(p, x, y, w, 11, (22, 28, 42))
    box(p, x, y + 11, w, 1, (84, 100, 130)); box(p, x, y + h - 4, w, 4, (14, 18, 28))
    box(p, x, y, 1, h, (60, 72, 96)); box(p, x + w - 1, y, 1, h, (12, 14, 22))
    box(p, x + 5, y + 2, 36, 8, (4, 12, 16))
    if alive:
        p.setPen(QColor(80, 230, 255) if st.vf != 2 else QColor(210, 120, 255))
        amp = 3 if st.vf != 2 else 4.5
        for i in range(36):
            v = amp * math.sin(t * 5 + i * .55) * math.sin(t * 1.3 + i * .13)
            if st.vf == 2:
                v += math.sin(t * 17 + i * 2.1) * 1.5
            p.drawPoint(int(x + 5 + i), int(y + 6 + v))
    else:
        p.setPen(QColor(36, 60, 70))
        p.drawLine(int(x + 5), int(y + 6), int(x + 40), int(y + 6))
    for i in range(3):
        cx, cy = x + 52 + i * 14, y + 19
        p.setPen(QPen(QColor(110, 120, 140), 1)); p.setBrush(QColor(12, 16, 24))
        p.drawEllipse(QPointF(cx, cy), 5, 5)
        a = (t if alive else 0) * (.4 + i * .25) + i * 2
        p.setPen(QColor(255, 176, 60))
        p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(a) * 4, cy + math.sin(a) * 4))
    for i in range(6):
        hg = 2 + int(5 * (.5 + .5 * math.sin(t * 4 + i * 1.3))) if alive else 1
        c = (90, 255, 150) if i < 3 else (255, 176, 60) if i < 5 else (255, 80, 80)
        box(p, x + w - 30 + i * 4, y + h - 6 - hg, 3, hg, c if alive else (40, 44, 52))
    # fuse slot: blinks amber until the transmitter is repaired, then glows green
    if "fixed" in st.flags:
        box(p, x + w - 6, y + 3, 3, 3, (90, 255, 150))
    elif (t * 2) % 1 < .5:
        box(p, x + w - 6, y + 3, 3, 3, (255, 176, 60) if st.vf == 1 else (255, 80, 80))


def _computer(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x, y + 16, w, h - 16, (70, 50, 36)); box(p, x, y + 16, w, 2, (112, 82, 58))
    box(p, x + 10, y, 28, 20, (26, 30, 38)); box(p, x + 12, y + 2, 24, 14, (4, 22, 12))
    if st.vf == 1:
        for k in range(5):
            lw = 4 + ((k + int(t * 4)) * 7) % 18
            box(p, x + 13, y + 3 + k * 2, lw, 1, (120, 240, 255, 230))
    elif st.vf == 2:
        for k in range(5):
            for j in range(4):
                if math.sin(t * 9 + k * 3.1 + j * 1.7) > -.2:
                    box(p, x + 13 + j * 5, y + 3 + k * 2, 3, 1, (220, 130, 255, 230))
    else:
        for k in range(5):
            box(p, x + 13, y + 3 + k * 2, 4 + (k * 7) % 18, 1, (60, 150, 100, 150))   # frozen log
    if (t * 2) % 1 < .5:
        box(p, x + 13, y + 14, 3, 1, (180, 255, 200))
    box(p, x + 8, y + 22, 30, 3, (40, 44, 54))


def _rack(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x, y, w, h, (20, 24, 34)); box(p, x, y, w, 1, (70, 80, 104))
    box(p, x, y, 1, h, (50, 58, 78)); box(p, x + w - 1, y, 1, h, (10, 12, 18))
    leds = [(90, 255, 150), (255, 176, 60), (255, 80, 80)]
    for u in range(5):
        uy = y + 3 + u * 8
        box(p, x + 2, uy, w - 4, 7, (30, 36, 50)); box(p, x + 2, uy, w - 4, 1, (62, 72, 94))
        for l in range(3):
            on = math.sin(t * (2 + u * .7) + l * 1.9 + u + x) > .2
            box(p, x + 4 + l * 4, uy + 3, 2, 2, leds[l] if on else (30, 42, 40))
        if u == 2:
            for cx in (x + 8, x + 21):
                p.setPen(QPen(QColor(140, 150, 170), 1)); p.setBrush(QColor(8, 10, 14))
                p.drawEllipse(QPointF(cx, uy + 3.5), 3, 3)
                a = t * 3
                p.drawLine(QPointF(cx, uy + 3.5), QPointF(cx + math.cos(a) * 2.5, uy + 3.5 + math.sin(a) * 2.5))
        else:
            box(p, x + w - 10, uy + 2, 6, 3, (12, 14, 20))


def _table(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x, y, w, 12, (104, 72, 48)); box(p, x, y, w, 1, (140, 102, 70))
    box(p, x, y + 12, w, 4, (64, 42, 28))
    box(p, x + 3, y + 16, 4, h - 16, (52, 34, 22)); box(p, x + w - 7, y + 16, 4, h - 16, (52, 34, 22))
    box(p, x + 12, y + 2, 16, 9, (206, 200, 178))
    for k in range(3):
        box(p, x + 14, y + 4 + k * 2, 11, 1, (120, 116, 100))
    box(p, x + 34, y + 3, 5, 6, (150, 70, 60))
    f = lamp_flicker(t)
    lx = x + w - 15
    box(p, lx, y - 8, 1, 12, (40, 40, 40))
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(int(230 * f), int(150 * f), int(50 * f)))
    p.drawPolygon(QPolygonF([QPointF(lx - 5, y - 8), QPointF(lx + 6, y - 8), QPointF(lx + 9, y - 2), QPointF(lx - 8, y - 2)]))
    box(p, lx - 2, y - 1, 4, 2, (255, int(230 * f), int(150 * f)))


def _chair(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x + 2, y, w - 4, 9, (70, 52, 44)); box(p, x, y + 8, w, 6, (54, 40, 34))
    box(p, x + 1, y + 14, 2, 4, (30, 22, 18)); box(p, x + w - 3, y + 14, 2, 4, (30, 22, 18))


def _cabinet(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x, y, w, h, (66, 74, 86)); box(p, x, y, w, 1, (110, 122, 138))
    for i in range(3):
        box(p, x + 2, y + 3 + i * 10, w - 4, 9, (54, 62, 74))
        box(p, x + w // 2 - 3, y + 7 + i * 10, 6, 1, (160, 170, 180))


def _shelf(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    r = random.Random(int(x))
    box(p, x, y, w, h, (58, 40, 30)); box(p, x, y + 14, w, 2, (92, 66, 48)); box(p, x, y, w, 1, (92, 66, 48))
    cx = x + 2
    while cx < x + w - 6:
        bw = r.randint(3, 6)
        box(p, cx, y + 14 - r.randint(8, 12), bw, 12, (r.randint(60, 150), r.randint(40, 90), r.randint(40, 100)))
        cx += bw + 1
    cx = x + 3
    while cx < x + w - 8:
        c = r.choice([(70, 120, 110), (150, 120, 60), (90, 90, 130)])
        box(p, cx, y + 20, 6, 8, c); box(p, cx, y + 20, 6, 1, (230, 230, 230, 120))
        cx += 9


def _crate(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x, y, w, h, (92, 66, 42)); box(p, x, y, w, 2, (128, 96, 64))
    box(p, x, y + h - 2, w, 2, (54, 38, 24)); box(p, x, y, 2, h, (60, 42, 26)); box(p, x + w - 2, y, 2, h, (60, 42, 26))
    p.setPen(QPen(QColor(60, 42, 26), 1))
    p.drawLine(int(x + 2), int(y + 2), int(x + w - 2), int(y + h - 2))
    p.drawLine(int(x + w - 2), int(y + 2), int(x + 2), int(y + h - 2))


def _plant(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x + 3, y + h - 10, 10, 10, (120, 70, 50)); box(p, x + 3, y + h - 10, 10, 2, (150, 94, 70))
    p.setPen(QColor(94, 72, 40))
    for tx, ty in ((x + 3, y + 5), (x + 8, y), (x + 13, y + 7)):
        p.drawLine(int(x + 8), int(y + h - 10), int(tx), int(ty))
        box(p, tx - 1, ty, 3, 2, (110, 90, 40))
    g = int(160 + 90 * math.sin(t * 3))
    if st.vf == 1:
        for lx, ly in ((x - 3, y + 8), (x + 12, y + 3), (x + 14, y + 12), (x + 1, y + 14)):
            p.setPen(QPen(QColor(60, 170, 90), 1)); p.drawLine(int(x + 8), int(y + h - 10), int(lx), int(ly))
            box(p, lx - 2, ly - 1, 5, 3, (70, 200, 100))
    box(p, x + 12, y + 5, 3, 3, (60, g, 110))


def _artifact(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x + 6, y + 30, 22, 14, (48, 50, 66)); box(p, x + 4, y + 28, 26, 3, (76, 80, 100))
    if st.vf == 1:
        return    # in the past there is only the empty pedestal
    wild = 2 if st.vf == 2 else 1
    cx, cy = x + 17, y + 14 + math.sin(t * 2) * 3
    p.setPen(QPen(QColor(255, 80, 200, 130), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(cx, cy), 12, 4)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(200, 60, 170))
    p.drawPolygon(QPolygonF([QPointF(cx, cy - 12), QPointF(cx + 7, cy), QPointF(cx, cy + 12), QPointF(cx - 7, cy)]))
    p.setBrush(QColor(255, 170, 240))
    p.drawPolygon(QPolygonF([QPointF(cx, cy - 7), QPointF(cx + 3, cy), QPointF(cx, cy + 7), QPointF(cx - 3, cy)]))
    for k in range(2 * wild):
        a = t * 2.2 + k * math.pi / wild
        p.setBrush(QColor(255, 200, 250))
        p.drawRect(int(cx + math.cos(a) * 12 * wild), int(cy + math.sin(a) * 4 * wild), 2, 2)


def _door(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    if "door_open" in st.flags:
        box(p, x + 12, y, w - 12, 3, (36, 40, 52)); box(p, x + 12, y + h - 3, w - 12, 3, (36, 40, 52))
        for i in range(4):
            box(p, x + 14, y + 8 + i * 14, 10, 2, (80, 230, 255, 160 + int(80 * math.sin(t * 4 + i))))
        return
    box(p, x, y, w, h, (36, 40, 52)); box(p, x + 3, y + 3, w - 6, h - 6, (58, 64, 78))
    box(p, x + 3, y + h // 2, w - 6, 1, (30, 34, 44)); box(p, x + 3, y + 3, 1, h - 6, (96, 106, 126))
    for i in range(0, int(w) - 6, 4):
        box(p, x + 3 + i, y + h - 12, 2, 5, (230, 190, 40)); box(p, x + 5 + i, y + h - 12, 2, 5, (20, 20, 24))
    box(p, x + 5, y + 24, 8, 12, (16, 18, 24))
    if "fixed" in st.flags:
        box(p, x + 7, y + 26, 4, 2, (90, 255, 150) if (t * 3) % 1 < .7 else (30, 80, 50))
    elif (t * 1.2) % 1 < .6:
        box(p, x + 7, y + 26, 4, 2, (255, 80, 80))
    # tone lamps: one per tone already entered, coloured by the frequency that was sent
    for i in range(3):
        c = TINT[st.seq[i]] if i < len(st.seq) else (30, 34, 44)
        box(p, x + 5 + i * 5, y + 40, 3, 3, c)


def _switch(p, pr, t, st):
    x, y = pr.rect.x(), pr.rect.y()
    box(p, x, y, 10, 14, (120, 126, 138)); box(p, x + 3, y + 3, 4, 8, (50, 54, 64))
    on = st.lights_on
    box(p, x + 4, y + 3 if on else y + 7, 2, 4, (245, 245, 245))
    box(p, x + 1, y + 1, 2, 2, (90, 255, 150) if on else (255, 80, 80))


def _rubble(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    r = random.Random(5)
    for row in range(int(h // 6) + 1):
        for col in range(int(w // 6) + 1):
            if r.random() < .25 + .75 * (row / (h / 6)):     # denser toward the floor
                s = r.randint(40, 78)
                box(p, x + col * 6 + r.randint(-1, 1), y + row * 6 + r.randint(-1, 1), r.randint(5, 9), r.randint(4, 8), (s, s - 4, s + 6))
                box(p, x + col * 6, y + row * 6, 4, 1, (s + 36, s + 32, s + 44))
    p.setPen(QPen(QColor(78, 54, 36), 2))
    p.drawLine(int(x - 3), int(y + h - 6), int(x + w - 6), int(y + 8))
    p.drawLine(int(x + 6), int(y + h - 2), int(x + w + 2), int(y + 16))
    if st.vf == 2:
        p.setPen(QColor(190, 90, 255, 90 + int(60 * math.sin(t * 5))))
        p.drawRect(int(x), int(y), int(w), int(h))


def _arch(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    a = 150 + int(60 * math.sin(t * 3))
    box(p, x, y - 4, 4, h + 4, (90, 170, 190)); box(p, x + w - 4, y - 4, 4, h + 4, (90, 170, 190))
    box(p, x, y - 6, w, 4, (110, 200, 220))
    box(p, x + w // 2 - 3, y - 2, 6, 3, (255, 240, 200, a))
    for i in range(3):
        box(p, x + 8, y + 10 + i * 12, w - 16, 1, (150, 240, 255, 70))


def _echo(p, pr, t, st):
    x, y = pr.rect.x(), pr.rect.y()
    p.save()
    p.setOpacity(.4 + .12 * math.sin(t * 7) + (.25 if math.sin(t * 31) > .93 else 0))
    box(p, x + 8, y, 9, 9, (140, 235, 255)); box(p, x + 6, y - 1, 13, 3, (100, 190, 215))
    box(p, x + 5, y + 9, 15, 14, (110, 210, 235))
    sc = int(math.sin(t * 6) * 2)
    box(p, x + 2, y + 12 + sc, 4, 8, (110, 210, 235)); box(p, x + 19, y + 12 - sc, 4, 8, (110, 210, 235))
    box(p, x + 5, y + 23, 15, 4, (80, 160, 185))
    for yy in range(0, 30, 4):
        p.fillRect(int(x), int(y + yy), 26, 1, QColor(0, 20, 30, 120))
    p.restore()


def _veil(p, pr, t, st):
    r = pr.rect
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    if st.vf == 2:
        a = 110 + int(70 * math.sin(t * 4 + x))
        p.setPen(QPen(QColor(190, 90, 255, a), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(int(x), int(y), int(w) - 1, int(h) - 1)
        p.setPen(QColor(220, 140, 255, 80))
        if w > h:
            for i in range(0, int(w), 3):
                p.drawLine(int(x + i), int(y), int(x + i), int(y + h * (.4 + .6 * math.sin(t * 6 + i))))
        else:
            for i in range(0, int(h), 3):
                p.drawLine(int(x), int(y + i), int(x + w * (.4 + .6 * math.sin(t * 6 + i))), int(y + i))
        return
    box(p, x, y, w, h, (46, 52, 66)); box(p, x, y, w, 1, (96, 108, 132)); box(p, x, y + h - 1, w, 1, (18, 20, 28))
    if w > h:
        for i in range(4, int(w), 10):
            box(p, x + i, y + 3, 2, 2, (20, 22, 30))
    else:
        for i in range(4, int(h), 10):
            box(p, x + 5, y + i, 2, 2, (20, 22, 30))


def _fuse(p, pr, t, st):
    x, y = pr.rect.x(), pr.rect.y() + math.sin(t * 3) * 2
    box(p, x + 2, y + 1, 8, 10, (230, 200, 255)); box(p, x + 1, y, 10, 2, (150, 150, 170)); box(p, x + 1, y + 10, 10, 2, (150, 150, 170))
    box(p, x + 5, y + 3, 2, 6, (255, 120, 220))


def _glyphs(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    for i in range(6):
        a = 120 + int(100 * math.sin(t * 2 + i))
        _glyph(p, int(x + (i % 3) * 15), int(y + (i // 3) * 18), 300 + i, QColor(220, 130, 255, a))
    a = 160 + int(80 * math.sin(t * 3))
    p.setPen(QPen(QColor(255, 180, 255, a), 2))
    p.drawLine(int(x + 8), int(y + h - 2), int(x + w - 6), int(y + h + 8)); p.drawLine(int(x + w - 12), int(y + h + 8), int(x + w - 6), int(y + h + 8))


def _sigil(p, pr, t, st):
    cx, cy = pr.rect.center().x(), pr.rect.center().y()
    a = 120 + int(80 * math.sin(t * 2.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(210, 120, 255, a), 1)); p.drawEllipse(QPointF(cx, cy), 13, 7)
    for k in range(3):
        ang = t * .8 + k * 2.094
        p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(ang) * 13, cy + math.sin(ang) * 7))
        p.fillRect(int(cx + math.cos(ang) * 13), int(cy + math.sin(ang) * 7), 2, 2, QColor(255, 180, 255, 230))


def _board(p, pr, t, st):
    """Standing board (duty board / whiteboard / slate): frame, pale face, a few scribbled lines, a red circle."""
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x + 3, y + h - 8, 3, 8, (50, 40, 32)); box(p, x + w - 6, y + h - 8, 3, 8, (50, 40, 32))
    box(p, x, y, w, h - 8, (92, 82, 70))
    box(p, x + 2, y + 2, w - 4, h - 12, (176, 180, 170))
    w, h = int(w), int(h)
    r = random.Random(int(x))
    for i in range(3):
        box(p, x + 4, y + 5 + i * 5, r.randint(w // 3, w - 10), 1, (70, 78, 96))
    box(p, x + w - 11, y + h - 17, 6, 1, (170, 60, 60)); box(p, x + w - 11, y + h - 22, 6, 1, (170, 60, 60))
    box(p, x + w - 11, y + h - 22, 1, 6, (170, 60, 60)); box(p, x + w - 6, y + h - 22, 1, 6, (170, 60, 60))


def _drawing(p, pr, t, st):
    """A child's crayon drawing pinned to the wall: paper, a few crayon strokes (colours differ per position)."""
    x, y = pr.rect.x(), pr.rect.y()
    box(p, x, y, 16, 20, (196, 190, 170)); box(p, x, y, 16, 1, (230, 224, 200)); box(p, x + 7, y - 1, 2, 2, (170, 50, 50))
    r = random.Random(int(x))
    for _ in range(4):
        box(p, x + r.randint(2, 11), y + r.randint(4, 15), r.randint(2, 4), 1, r.choice(((220, 150, 40), (60, 140, 200), (200, 70, 70), (80, 170, 90))))


def _safe(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    opened = "safe_open" in st.flags
    box(p, x, y + h - 6, w, 6, (40, 44, 54))                                 # trolley
    box(p, x, y, w, h - 6, (58, 64, 78)); box(p, x, y, w, 1, (110, 122, 142)); box(p, x, y, 1, h - 6, (92, 102, 122))
    if opened:
        box(p, x + 3, y + 3, w - 6, h - 12, (12, 14, 20)); box(p, x + 5, y + 8, 8, 8, (200, 192, 160))
    else:
        for i in range(3):
            box(p, x + 4 + i * 6, y + 6, 4, 4, (150, 160, 176))
        box(p, x + w - 6, y + 14, 3, 5, (190, 160, 70))


def _locker(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    opened = (pr.sid or "locker") + "_open" in st.flags
    box(p, x, y, w, h, (62, 72, 88)); box(p, x, y, w, 1, (112, 126, 148)); box(p, x, y, 1, h, (96, 108, 128))
    if opened:
        box(p, x + 3, y + 3, w - 6, h - 6, (14, 16, 22)); box(p, x + 3, y + 3, 3, h - 6, (84, 96, 118))
        box(p, x + 10, y + 14, 8, 10, (190, 184, 160))
    else:
        for i in range(4):
            box(p, x + 4, y + 4 + i * 2, w - 8, 1, (38, 44, 56))
        box(p, x + w - 8, y + h // 2 - 4, 3, 8, (150, 160, 176))
        lit = .5 + .5 * math.sin(t * 3)
        box(p, x + w // 2 - 3, y + h // 2 + 6, 6, 6, (40, 48, 60)); box(p, x + w // 2 - 1, y + h // 2 + 8, 2, 2, (255, int(150 + 60 * lit), 60))


def _plaque(p, pr, t, st):
    x, y = pr.rect.x(), pr.rect.y()
    box(p, x, y, 14, 14, (140, 112, 50)); box(p, x, y, 14, 1, (200, 170, 90)); box(p, x + 1, y + 13, 13, 1, (80, 62, 28))
    for i in range(3):
        box(p, x + 2, y + 3 + i * 3, 10, 1, (64, 50, 24))


def _beacon(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    cx = x + w / 2
    box(p, x + 6, y + h - 12, w - 12, 12, (40, 48, 64)); box(p, x + 6, y + h - 12, w - 12, 2, (90, 104, 132))
    box(p, cx - 3, y + 14, 6, h - 26, (58, 66, 84)); box(p, cx - 3, y + 14, 1, h - 26, (110, 124, 150))
    f = st.vf
    col = ((90, 70, 40), (80, 230, 255), (200, 100, 255))[f]
    pulse = .5 + .5 * math.sin(t * (2 if f else .6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for k in range(3):
        ph = (t * (.6 if f else .15) + k / 3) % 1
        p.setPen(QPen(QColor(col[0], col[1], col[2], int((200 if f else 70) * (1 - ph))), 1))
        p.drawEllipse(QPointF(cx, y + 14), 6 + ph * 22, 3 + ph * 10)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(col[0], col[1], col[2], 120 + int(120 * pulse)))
    p.drawEllipse(QPointF(cx, y + 12), 5, 5)
    if f == 2:
        for k in range(10):
            yy = y + h - 14 - ((t * 24 + k * 13) % (h - 14))
            p.fillRect(int(cx + math.sin(t * 2 + k) * 8), int(yy), 1, 2, QColor(230, 160, 255, 200))
    box(p, x + 10, y + h - 9, 4, 3, col if f else (60, 50, 34))


def _mural(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    f = st.vf
    box(p, x - 2, y - 2, w + 4, h + 4, (16, 18, 26))
    if f == 2:
        box(p, x, y, w, h, (12, 4, 28))
        r = random.Random(9)
        for i in range(30):
            box(p, x + r.randint(2, int(w) - 3), y + r.randint(2, int(h) - 3), 1, 1, (230, 190, 255))
        a = 140 + int(110 * math.sin(t * 3))
        box(p, x + int(w * .62), y + int(h * .4), 3, 3, (255, 120, 220, a))
    elif f == 1:
        box(p, x, y, w, h, (30, 90, 120)); box(p, x, y + h * .6, w, h * .4, (14, 50, 80))
        box(p, x + 50, y + 14, 6, 18, (230, 230, 220)); box(p, x + 48, y + 12, 10, 3, (255, 90, 80))
        box(p, x + 30, y + 22, 14, 10, (150, 120, 90))
    else:
        box(p, x, y, w, h, (60, 54, 46)); box(p, x, y + h * .6, w, h * .4, (40, 42, 44))
        p.setPen(QPen(QColor(24, 22, 20), 2))
        p.drawLine(int(x + 52), int(y + 22), int(x + 80), int(y + 38))
        box(p, x + 30, y + 22, 14, 10, (86, 74, 60))


def _oldradio(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    powered = "fixed" in st.flags
    box(p, x + 4, y + 22, 4, 8, (50, 34, 22)); box(p, x + w - 8, y + 22, 4, 8, (50, 34, 22))     # legs
    box(p, x, y + 4, w, 20, (104, 70, 42)); box(p, x, y + 4, w, 1, (150, 106, 68)); box(p, x, y + 23, w, 1, (56, 36, 22))
    for i in range(5):                                                                          # speaker grille
        box(p, x + 3, y + 8 + i * 3, 12, 1, (50, 34, 22))
    box(p, x + 18, y + 7, 11, 9, (14, 16, 20))                                                   # dial window
    if powered:
        c = TINT[st.vf]
        box(p, x + 18, y + 7, 11, 9, (c[0] // 4, c[1] // 4, c[2] // 4))
        nx = x + 19 + (st.dial - 86) / 38 * 9
        box(p, nx, y + 8, 1, 7, (255, 255, 255))
        box(p, x + 18, y + 7, 11, 1, (*c, 200))
    else:
        p.setPen(QColor(90, 100, 110)); p.drawLine(int(x + 18), int(y + 7), int(x + 29), int(y + 16))   # crack
    box(p, x + 20, y + 18, 3, 3, (180, 160, 120)); box(p, x + 25, y + 18, 3, 3, (180, 160, 120))
    p.setPen(QPen(QColor(150, 150, 160), 1)); p.drawLine(int(x + w - 5), int(y + 4), int(x + w + 3), int(y - 8))  # antenna


def _notebook(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x, y + 10, w, 12, (94, 66, 44)); box(p, x, y + 10, w, 1, (136, 100, 68)); box(p, x, y + 22, w, 3, (54, 36, 24))
    box(p, x + 3, y + 25, 4, h - 25, (50, 34, 22)); box(p, x + w - 7, y + 25, 4, h - 25, (50, 34, 22))
    box(p, x + 14, y + 4, 26, 12, (214, 206, 180)); box(p, x + 26, y + 4, 1, 12, (150, 140, 110))
    for k in range(3):
        box(p, x + 16, y + 6 + k * 3, 8, 1, (110, 100, 80)); box(p, x + 29, y + 6 + k * 3, 8, 1, (110, 100, 80))
    if st.vf == 2:
        a = 140 + int(100 * math.sin(t * 3))
        box(p, x + 30, y + 6, 6, 1, (220, 130, 255, a)); box(p, x + 30, y + 9, 4, 1, (220, 130, 255, a))
    box(p, x + 44, y + 8, 8, 2, (200, 170, 50))      # pencil


def _secdoor(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    if "archive_open" in st.flags:
        box(p, x + 12, y, w - 12, 3, (44, 40, 56)); box(p, x + 12, y + h - 3, w - 12, 3, (44, 40, 56))
        for i in range(4):
            box(p, x + 14, y + 8 + i * 14, 10, 2, (255, 190, 110, 150 + int(80 * math.sin(t * 4 + i))))
        return
    box(p, x, y, w, h, (44, 40, 56)); box(p, x + 3, y + 3, w - 6, h - 6, (66, 62, 82))
    box(p, x + 3, y + 3, 1, h - 6, (110, 106, 132)); box(p, x + 3, y + h // 2, w - 6, 1, (34, 32, 44))
    for i in range(0, int(w) - 6, 4):
        box(p, x + 3 + i, y + h - 12, 2, 5, (230, 190, 40)); box(p, x + 5 + i, y + h - 12, 2, 5, (20, 20, 24))
    box(p, x + 5, y + 20, 10, 16, (18, 18, 26))
    for r in range(3):
        for c in range(2):
            box(p, x + 6 + c * 4, y + 22 + r * 4, 3, 3, (70, 74, 96))
    on = (t * 1.5) % 1 < .6
    box(p, x + 7, y + 16, 6, 2, (255, 70, 70) if on else (90, 30, 30))      # locked indicator


def _archive(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    r = random.Random(int(x))
    box(p, x, y, w, h, (46, 36, 34)); box(p, x, y, w, 1, (84, 68, 62)); box(p, x, y + 15, w, 2, (70, 56, 50))
    for row in (0, 1):
        cx = x + 2
        while cx < x + w - 6:
            bw = r.randint(3, 6)
            bh = r.randint(8, 12)
            box(p, cx, y + 15 + row * 17 - bh, bw, bh, (r.randint(70, 150), r.randint(60, 110), r.randint(60, 100)))
            cx += bw + 1


def _receiver(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    active = "p3_done" in st.flags
    box(p, x + 2, y + h - 8, w - 4, 8, (30, 34, 44))
    box(p, x, y + 14, w, h - 20, (50, 58, 74)); box(p, x, y + 14, w, 2, (110, 124, 150)); box(p, x, y + h - 8, w, 2, (22, 26, 34))
    box(p, x + 5, y + 20, 30, 22, (4, 14, 18))                                                    # scope screen
    col = QColor(*TINT[st.vf])
    p.setPen(QPen(col if active else QColor(40, 70, 80), 1))
    for i in range(30):
        v = (7 * math.sin(t * 10 + i * .6) * math.sin(t + i * .1)) if active else 0
        p.drawPoint(int(x + 5 + i), int(y + 31 + v))
    for i in range(3):                                                                            # three tone lamps
        c = TINT[(0, 2, 1)[i]]
        box(p, x + 40, y + 20 + i * 8, 6, 5, c if active or int(t * 2) % 3 == i else (28, 32, 40))
    for k in range(2):                                                                            # coils on top
        cx = x + 12 + k * 28
        box(p, cx, y + 2, 6, 14, (70, 54, 40)); box(p, cx - 2, y, 10, 3, (120, 100, 70))
        for j in range(5):
            box(p, cx, y + 4 + j * 2, 6, 1, (170, 120, 60))
    if active:
        ring = (t * .7) % 1
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), int(200 * (1 - ring))), 1))
        p.drawEllipse(QPointF(x + w / 2, y + 2), 8 + ring * 28, 4 + ring * 12)
    box(p, x + 8, y + h - 14, 5, 3, (200, 170, 90)); box(p, x + 18, y + h - 14, 5, 3, (200, 170, 90))


def _sidetable(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x, y, w, 10, (96, 68, 46)); box(p, x, y, w, 1, (140, 104, 72)); box(p, x, y + 10, w, 3, (58, 40, 28))
    box(p, x + 3, y + 13, 4, h - 13, (52, 36, 24)); box(p, x + w - 7, y + 13, 4, h - 13, (52, 36, 24))
    box(p, x + 8, y + 2, 12, 5, (200, 196, 176)); box(p, x + 9, y + 3, 9, 1, (110, 106, 92))    # scribbled note


def _echorecv(p, pr, t, st):
    """The handheld on the table (crisp small pixel version). Pulses so it draws the eye."""
    x, y = pr.rect.x(), pr.rect.y()
    pulse = .5 + .5 * math.sin(t * 4)
    box(p, x + 10, y + 2, 1, 8, (150, 156, 168)); box(p, x + 11, y, 2, 2, (80, 230, 255, 140 + int(100 * pulse)))
    box(p, x + 1, y + 9, 12, 17, (30, 34, 40)); box(p, x, y + 8, 12, 17, (74, 82, 70)); box(p, x, y + 8, 12, 1, (122, 134, 112))
    box(p, x + 2, y + 11, 8, 5, (3, 14, 18))
    p.setPen(QColor(80, 230, 255))
    for i in range(8):
        p.drawPoint(int(x + 2 + i), int(y + 13 + 1.6 * math.sin(t * 8 + i)))
    box(p, x + 2, y + 18, 4, 4, (50, 56, 48)); box(p, x + 3, y + 19, 2, 2, (200, 200, 190))
    box(p, x + 7, y + 18, 2, 1, (90, 255, 150) if pulse > .5 else (30, 60, 40)); box(p, x + 7, y + 20, 2, 1, (255, 176, 60))


def _source(p, pr, t, st):
    """A hidden transmission source, only drawn while tracking and brighter the closer you stand."""
    c = pr.rect.center()
    d = math.hypot(c.x() - st.player.x, c.y() - st.player.y)
    k = max(0.0, 1 - d / 130)
    if k <= 0:
        return
    col = TINT[st.vf]
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(3):
        ph = (t * .8 + i / 3) % 1
        p.setPen(QPen(QColor(col[0], col[1], col[2], int(220 * k * (1 - ph))), 1))
        p.drawEllipse(QPointF(c.x(), c.y()), 3 + ph * 18, (3 + ph * 18) * .6)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, int(200 * k)))
    p.drawEllipse(QPointF(c.x(), c.y() + math.sin(t * 5) * 1.5), 2, 2)
    for j in range(4):
        a = t * 2 + j * 1.57
        p.fillRect(int(c.x() + math.cos(a) * 9 * k), int(c.y() + math.sin(a) * 5 * k), 1, 1, QColor(col[0], col[1], col[2], int(240 * k)))


def _chamberdoor(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    if "chamber_open" in st.flags:
        box(p, x + 12, y, w - 12, 3, (50, 46, 80)); box(p, x + 12, y + h - 3, w - 12, 3, (50, 46, 80))
        for i in range(4):
            box(p, x + 14, y + 8 + i * 14, 10, 2, (190, 120, 255, 150 + int(80 * math.sin(t * 4 + i))))
        return
    box(p, x, y, w, h, (40, 36, 64)); box(p, x + 3, y + 3, w - 6, h - 6, (62, 56, 96))
    box(p, x + 3, y + 3, 1, h - 6, (120, 112, 170)); box(p, x + 3, y + h // 2, w - 6, 1, (30, 28, 50))
    for i in range(0, int(w) - 6, 4):
        box(p, x + 3 + i, y + h - 12, 2, 5, (230, 190, 40)); box(p, x + 5 + i, y + h - 12, 2, 5, (20, 20, 24))
    box(p, x + 5, y + 20, 10, 16, (16, 16, 26))
    for r in range(3):
        for c in range(2):
            box(p, x + 6 + c * 4, y + 22 + r * 4, 3, 3, (90, 84, 130))
    box(p, x + 7, y + 16, 6, 2, (190, 90, 255) if (t * 1.5) % 1 < .6 else (70, 30, 100))


def _datepanel(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    f = st.vf
    if f == 0:      # wall calendar, the 14th circled
        box(p, x, y, w, h, (214, 206, 180)); box(p, x, y, w, 5, (170, 50, 50))
        for r in range(3):
            for c in range(4):
                box(p, x + 3 + c * 4, y + 8 + r * 5, 2, 2, (110, 100, 80))
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(220, 40, 40), 1)); p.drawEllipse(QPointF(x + 11, y + 15), 4, 4)
    elif f == 1:    # faded office calendar: AUGUST
        box(p, x, y, w, h, (186, 176, 140)); box(p, x, y, w, 5, (90, 110, 150))
        for r in range(3):
            for c in range(4):
                box(p, x + 3 + c * 4, y + 8 + r * 5, 2, 2, (120, 110, 84))
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(200, 60, 60), 1)); p.drawEllipse(QPointF(x + 11, y + 15), 4, 4)
    else:           # glowing digits on the floor
        a = 150 + int(90 * math.sin(t * 3))
        p.setPen(QPen(QColor(210, 130, 255, a), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(x + w / 2, y + h / 2), w / 2, h / 3)
        for i, seg in enumerate(((0, 0, 4, 0), (4, 0, 4, 5), (4, 5, 0, 5), (0, 5, 0, 9), (0, 9, 4, 9), (8, 0, 12, 0), (12, 0, 12, 9), (12, 9, 8, 9), (8, 9, 8, 0))):
            p.drawLine(int(x + 4 + seg[0]), int(y + 6 + seg[1]), int(x + 4 + seg[2]), int(y + 6 + seg[3]))


def _finaltx(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    ready = "final_ready" in st.flags
    box(p, x + 4, y + h - 10, w - 8, 10, (34, 32, 52)); box(p, x, y + 20, w, h - 28, (52, 50, 78)); box(p, x, y + 20, w, 2, (120, 116, 170))
    for k in range(3):                                              # three tall coils, one per band
        cx = x + 10 + k * 24
        col = TINT[(2, 0, 1)[k]]
        box(p, cx, y, 10, 26, (70, 56, 44)); box(p, cx - 2, y - 2, 14, 3, (130, 108, 76))
        for j in range(6):
            box(p, cx, y + 3 + j * 3, 10, 1, (190, 130, 70))
        lit = ready or (int(t * 2) % 3 == k)
        box(p, cx + 3, y + 28, 4, 4, col if lit else (30, 30, 44))
    box(p, x + 8, y + 40, 56, 14, (4, 8, 12))
    p.setPen(QColor(190, 90, 255) if not ready else QColor(255, 230, 150))
    for i in range(56):
        v = (4 if ready else 2) * math.sin(t * 8 + i * .5)
        p.drawPoint(int(x + 8 + i), int(y + 47 + v))
    if ready:
        ring = (t * .8) % 1
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 230, 150, int(220 * (1 - ring))), 1))
        p.drawEllipse(QPointF(x + w / 2, y), 6 + ring * 40, 3 + ring * 20)


def _lectern(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x + 2, y + 12, w - 4, h - 12, (74, 54, 38)); box(p, x, y + 4, w, 10, (104, 76, 54)); box(p, x, y + 4, w, 1, (150, 112, 80))
    box(p, x + 4, y, w - 8, 8, (214, 206, 180)); box(p, x + 6, y + 2, w - 12, 1, (110, 100, 80)); box(p, x + 6, y + 5, w - 16, 1, (110, 100, 80))


def _rack09(p, pr, t, st):
    x, y, w, h = pr.rect.x(), pr.rect.y(), pr.rect.width(), pr.rect.height()
    box(p, x, y, w, h, (40, 44, 56)); box(p, x, y, w, 1, (100, 108, 130))
    for i in range(5):
        box(p, x + 3 + i * 7, y + 4, 5, h - 8, (90, 70, 50))
    a = 140 + int(100 * math.sin(t * 4))
    box(p, x + 17, y + 4, 5, h - 8, (255, 200, 90, a))                    # the warm reel: 09-A
    box(p, x + w - 6, y + 3, 3, 3, (90, 255, 150) if int(t * 2) % 2 else (30, 60, 40))


_DRAW = {"console": _console, "computer": _computer, "rack": _rack, "table": _table,
         "chair": _chair, "cabinet": _cabinet, "shelf": _shelf, "crate": _crate,
         "plant": _plant, "artifact": _artifact, "door": _door, "switch": _switch,
         "rubble": _rubble, "board": _board, "locker": _locker, "drawing": _drawing, "safe": _safe, "arch": _arch, "echo": _echo, "veil": _veil, "fuse": _fuse,
         "glyphs": _glyphs, "sigil": _sigil, "plaque": _plaque, "beacon": _beacon, "mural": _mural,
         "oldradio": _oldradio, "notebook": _notebook, "secdoor": _secdoor, "archive": _archive,
         "receiver": _receiver, "sidetable": _sidetable, "echorecv": _echorecv, "source": _source,
         "chamberdoor": _chamberdoor, "datepanel": _datepanel, "finaltx": _finaltx, "lectern": _lectern,
         "rack09": _rack09, "chterm": _computer}


def draw_prop(p, pr, t, st):
    _DRAW[pr.kind](p, pr, t, st)
