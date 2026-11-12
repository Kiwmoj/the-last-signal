"""Story manager data and logic: five chapters, their missions, and the story events (dialogue, radio talk, cards).

Everything is DERIVED from the saved flags, so Continue resumes exactly where the story was:
  * a mission is complete when its condition holds, checked strictly in order inside the current chapter
  * completing the last mission ends the chapter and starts the next
  * each completed mission/chapter queues its event; events that have not played yet (flag "evt_<id>")
    are re-queued after loading, so nothing is lost if you quit mid-scene.
Dialogue lines are (speaker, text, style) with style plain / radio / terminal / note / voice.
"""

def _j(*ids):
    return lambda gp: all(gp.journal.has(i) for i in ids)


def _f(flag):
    return lambda gp: flag in gp.flags


def _hint_track(gp):
    """Chapter 1 tracking hint: always names the next concrete step instead of a vague goal."""
    if not gp.radio_on:
        return "Switch your radio on  [SPACE]"
    if gp.eff != 1:
        return "Tune to 104.7 MHz, the Past  [Q]"
    if "echo_track" not in gp.flags:
        return "Echo [R]: press 2 for TRACK, then ENTER"
    return "Follow the arrow. It is in this room  [E] lock on"


class Mission:
    """`hint` is a string or a function(gp) -> string for hints that depend on what the player has done."""
    def __init__(self, mid, text, hint, done, event=None):
        self.id, self.text, self.hint, self.done, self.event = mid, text, hint, done, event


class Chapter:
    def __init__(self, n, title, hook, recap, missions, end_event=None, start_events=()):
        self.n, self.title, self.hook, self.recap = n, title, hook, recap
        self.missions, self.end_event, self.start_events = missions, end_event, list(start_events)


CHAPTERS = [
    Chapter(1, "THE ARRIVAL",
            "August 1997. Station 09 has been silent for seventeen years. Tonight, someone called it.",
            "You were sent to Station 09 after a dead station sent an emergency call. Inside, an Echo Receiver left by Dr. Elias Marlowe detected a signal still "
            "transmitting from the sealed research wing.",
            [Mission("c1m1", "Investigate the transmission", "Look around the control room  [WASD]", lambda gp: "evt_arrival" in gp.flags and "tut_move" in gp.flags),
             Mission("c1m2", "Enter Station 09", "Step deeper into the control room", _f("entered"), "entered"),
             Mission("c1m3", "Find the Echo Receiver", "Something on the side table is humming", _f("echo_found"), "echo_found"),
             Mission("c1m4", "Track the research wing signal", _hint_track, _f("src_tut"), "signal_found"),
             Mission("c1m5", "Replay it in the Echo's MEMORY", "Open the Echo [R], press 3 for MEMORY, then ENTER to play", _f("tut_done"))],
            end_event="c1end", start_events=["card1", "arrival"]),
    Chapter(2, "THE EMPTY STATION",
            "The research wing is sealed, the power is dead, and the station was abandoned in a hurry.",
            "Station 09 was evacuated in a panic on the night of the incident. You restored power and opened the research wing, guided by Marlowe's recordings.",
            [Mission("c2m1", "Explore the control room", "Terminal, filing cabinet, supply crate", _j("staff", "log_final", "evacuated", "belongings"), "explored"),
             Mission("c2m2", "Restore station power", "The Past remembers a spare fuse (104.7)", _f("fixed"), "power_on"),
             Mission("c2m3", "Find Elias's recording", "Track it with the Echo on the Unknown band", _f("src_elias"), "elias_heard"),
             Mission("c2m4", "Unlock the research wing", "Three tones, in Elias's order", _f("door_open"))],
            end_event="c2end", start_events=["card2", "c2start"]),
    Chapter(3, "THE ARCHIVE",
            "The wing is open. Whatever Station 09 was built for is waiting inside.",
            "The research wing held experiments on three frequencies. You rebuilt Marlowe's emergency transmission, opened the archive his daughter's name locked, "
            "and a live voice spoke your name.",
            [Mission("c3m1", "Enter the research wing", "The sealed door is open", _f("wing_entered"), "wing_enter"),
             Mission("c3m2", "Study the experiment array", "Examine it on all three frequencies", _f("beacon"), "array_done"),
             Mission("c3m3", "Reconstruct the missing message", "The old radio is wired to this wing's relay", _f("p1_done"), "p1_evt"),
             Mission("c3m4", "Unlock the archive", "Elias's log, Wren's notebook, a 121.3 file", _f("archive_open"), "archive_evt"),
             Mission("c3m5", "Wake the archive receiver", "Heaviest pulse count first. See the notebook", _f("p3_done")),
             Mission("c3m6", "Find the live voice", "Track it with the Echo Receiver", _f("final_signal"))],
            end_event="c3end", start_events=["card3", "c3start"]),
    Chapter(4, "THE UNKNOWN",
            "The voice knew your name. The station no longer agrees on what year it is.",
            "You followed Marlowe's echoes through the station and learned how the incident unfolded. At the archive you heard your own voice on a recording from 1997: "
            "you are the unknown signal.",
            [Mission("c4m1", "Follow the echoes: control room", "Where Elias last sat. Past band (104.7)", _f("src_trail1")),
             Mission("c4m2", "Follow the echoes: offices", "The offices and storage. Unknown band (121.3)", _f("src_trail2")),
             Mission("c4m3", "Follow the echoes: research wing", "The experiment bays. Present band (88.1)", _f("src_trail3"), "trail_end"),
             Mission("c4m4", "Play recording 09-A", "The rack in the archive", _f("revealed"), "reveal")],
            end_event="c4end", start_events=["card4", "c4start"]),
    Chapter(5, "THE LAST SIGNAL",
            "Everything points to one room. Whatever you decide, it ends tonight.",
            "You opened the transmission chamber, learned what Station 09 was built for, and reassembled the final transmission.",
            [Mission("c5m1", "Open the transmission chamber", "The date it began, written in 3 layers", _f("chamber_open"), "chamber_evt"),
             Mission("c5m2", "Learn the purpose of Station 09", "Read the chamber terminal's files", _j("purpose"), "purpose_evt"),
             Mission("c5m3", "Reconstruct the final transmission", "Unknown, present, past: see Elias's notes", _f("final_ready"), "final_evt"),
             Mission("c5m4", "Decide the fate of the signal", "Send the warning, or shut it down", _f("decision"))],
            end_event=None, start_events=["card5", "c5start"]),
]
BY_N = {c.n: c for c in CHAPTERS}

# Three escalating hints per mission (press K): a nudge, then where to look, then exactly what to do.
HINTS = {
    "c1m1": ["Get your bearings first.", "Walk around the control room with WASD.", "Hold D or the right arrow to walk into the room."],
    "c1m2": ["Go deeper into the room.", "Head east, past the middle of the control room.", "Walk to the red rug in the middle of the room."],
    "c1m3": ["Something on the left side table is humming.", "The table is at the far left of the room.", "Stand next to the small table on the left and press E."],
    "c1m4": ["The Echo Receiver finds hidden things.", "Radio on (SPACE), tune to 104.7 (Q), open the Echo (R) and choose TRACK.", "Follow the gold arrow to the signal and press E to lock on."],
    "c1m5": ["You have a recording. Replay it.", "Open the Echo with R and go to MEMORY (press 3).", "Press ENTER in MEMORY to play the recording."],
    "c2m1": ["Three things in this room hold answers.", "The terminal, the filing cabinet and the supply crate.", "Press E at each. The terminal's files change with the frequency, so read it on every band."],
    "c2m2": ["The Past remembers a spare fuse. The Unknown shows it.", "The fuse is in the Offices. The first time, the doorway only opens on 104.7.", "Take the fuse on 121.3 in the Offices, then use it at the Main Transmitter on 104.7."],
    "c2m3": ["Elias left a recording the Echo can find.", "It is in the control room, on the Unknown band (121.3).", "Echo TRACK on 121.3 in the control room, then lock on with E."],
    "c2m4": ["The research wing door wants three tones.", "Elias's recording named the order: memory, the dark, the present.", "Press E at the door on 104.7, then 121.3, then 88.1."],
    "c3m1": ["The wing is open now.", "Walk east through the research wing door.", "The door is on the right side of the offices."],
    "c3m2": ["The Experiment Array answers to all three bands.", "Examine it on 88.1, 104.7 and 121.3.", "Press E at the array on each frequency, using Q in between."],
    "c3m3": ["The old radio is wired to this wing.", "Use it and rebuild the message from the fragments. Each band holds one.", "The recording order is not the reading order: try the second fragment first, then the first, then the third."],
    "c3m4": ["The archive door wants a name and a year.", "The name is in the decrypted log (88.1), the year in the notebook (104.7).", "Type NORA1971 at the Archive Door."],
    "c3m5": ["The archive receiver wants pulses in a certain order.", "The notebook says the heaviest pulse count goes first.", "Order the pulse patterns from most pulses to fewest."],
    "c3m6": ["A live voice is somewhere in the archive.", "Use the Echo on the Unknown band, inside the archive.", "Echo TRACK on 121.3 in the archive and press E at the signal."],
    "c4m1": ["Follow the echoes. Begin where Elias last sat.", "The control room, on the Past band (104.7).", "Echo TRACK on 104.7 in the control room and lock on."],
    "c4m2": ["The trail continues through the offices.", "The Unknown band (121.3), in the offices and storage.", "Echo TRACK on 121.3 in the offices and lock on."],
    "c4m3": ["The trail reaches the research wing.", "The Present band (88.1), in the experiment bays.", "Echo TRACK on 88.1 in the research wing and lock on."],
    "c4m4": ["The trail ends in the archive.", "Look for a recording rack numbered 09-A.", "Press E at the rack in the archive."],
    "c5m1": ["The chamber door wants a date as six digits.", "Day, month and year are written on three calendars, one per frequency.", "Day on 88.1, month on 104.7, year on 121.3. Type them as DDMMYY."],
    "c5m2": ["The chamber terminal holds the purpose of Station 09.", "Its files are different on each frequency.", "Press E at the research terminal and read every file."],
    "c5m3": ["Elias's notes give the order.", "Unknown first, then the present, then the past.", "At the final transmitter send 121.3, then 88.1, then 104.7."],
    "c5m4": ["You have everything you need.", "Send the warning, or shut the signal down.", "Choose with A and D, then press ENTER."],
}


def hint_for(mission_id, level):
    h = HINTS.get(mission_id)
    return h[min(level, len(h) - 1)] if h else ""


# ---------------------------------------------------------------- events
# "lines": dialogue pages, "fx": a world effect run when the event starts
EVENTS = {
    "arrival": {"lines": [
        ("DISPATCH", "Alex, this is Dispatch. Do you copy? Over.", "radio"),
        ("ALEX", "Copy, Dispatch. I'm inside Station 09. The door locked behind me.", "plain"),
        ("DISPATCH", "That place has been dead since 1980. Seventeen years of nothing, and tonight somebody called it. Find out who.", "radio"),
        ("ALEX", "Understood. I'll start with this room.", "plain")], "fx": "door_lock"},
    "entered": {"lines": [
        ("ALEX", "The equipment is warm. After seventeen years of nothing.", "plain"),
        ("ALEX", "Somebody, or something, has been keeping this place alive.", "plain")], "fx": "flicker"},
    "echo_found": {"lines": [
        ("ALEX", "A handheld scanner. 'ECHO' scratched into the case, and initials on the back: E.M.", "plain"),
        ("ALEX", "Whoever E.M. was, they built this to hear things radios can't. Let's see what it hears.", "plain")]},
    "signal_found": {"lines": [
        ("ALEX", "Got it. A voice from the past, caught in the Echo. Replay it from MEMORY. I want to hear it again.", "plain")]},
    "c1end": {"lines": [
        ("ECHO RECEIVER", "SIGNAL DETECTED.  SOURCE: RESEARCH WING (SEALED).  STATUS: STILL TRANSMITTING.", "radio"),
        ("ALEX", "Seventeen years, and it's still broadcasting from behind that door.", "plain"),
        ("ALEX", "Whoever is in there wants me to hear it.", "plain")]},
    "c2start": {"lines": [
        ("ALEX", "No power, and the research wing is sealed. Before I break anything, I want to know what happened here.", "plain")]},
    "explored": {"lines": [
        ("ALEX", "A half-finished cup of coffee. A child's coat on the chair. Folders pulled out of the cabinet in a hurry.", "plain"),
        ("ALEX", "Nobody packs like that. They ran. And the research wing runs off the main transmitter's circuit. No power, no door.", "plain"),
        ("ALEX", "There has to be a spare fuse somewhere. The Past might remember where.", "plain")]},
    "power_on": {"lines": [
        ("ALEX", "The transmitter's alive. Lights, relays... even the old radio is whispering.", "plain"),
        ("ALEX", "Marlowe's echo said the wing is wired to this circuit. If he left more, the receiver should hear it.", "plain")], "fx": "lights_on"},
    "elias_heard": {"lines": [
        ("ALEX", "Three tones. Memory, the dark, the present. Every clue for the lock is somewhere in this station, each on its own band.", "plain")]},
    "c2end": {"lines": [
        ("ELIAS (RECORDING)", "If you have opened the wing, then it has already started listening to you.", "voice"),
        ("ELIAS (RECORDING)", "I am sorry. It was never supposed to answer.", "voice"),
        ("ALEX", "He knew someone would come.", "plain")]},
    "c3start": {"lines": [
        ("ALEX", "The wing is open. Whatever this station was really for, it's in there.", "plain")]},
    "wing_enter": {"lines": [
        ("ALEX", "Experiment bays. Dials labelled PRESENT, PAST... and a third with no label at all.", "plain")]},
    "array_done": {"lines": [
        ("ALEX", "They weren't studying radio. They were listening to time.", "plain"),
        ("ALEX", "The log says this wing's relay feeds the old radio in the control room. If the night's last transmission survived, it's there.", "plain")]},
    "p1_evt": {"lines": [
        ("ALEX", "Marlowe opened the archive to hear who was speaking. And he locked it with his daughter's name.", "plain"),
        ("ALEX", "The key is a name and a year. His log, Wren's notebook and the unknown band should give me both.", "plain")]},
    "archive_evt": {"lines": [
        ("ALEX", "'Do not open the archive.' That's what the call said.", "plain"),
        ("ALEX", "...Too late. And the receiver in here is still warm.", "plain")]},
    "c3end": {"lines": [
        ("ALEX", "It knew my name. It has heard my voice for seventeen years... that doesn't make any sense.", "plain"),
        ("ALEX", "Follow the echoes. Start where he last sat.", "plain")]},
    "c4start": {"lines": [
        ("ALEX", "The air just changed. For a second this room looked... different.", "plain")], "fx": "shift"},
    "trail_end": {"lines": [
        ("ALEX", "Marlowe asked it who it was. And it said: 'I am the one who will send this.'", "plain"),
        ("ALEX", "He opened the archive to hear. So the answer is in there, on a rack in the archive.", "plain")]},
    "reveal": {"lines": [
        ("ARCHIVE RACK 09-A", "Reel label: A. REYES.  AUGUST 1997.  03:33 AM.", "terminal"),
        ("ARCHIVE RACK 09-A", "Playing...", "terminal"),
        ("ALEX (RECORDING)", "Station 09... if anyone can hear this... do not open the archive... it knows you're listening.", "voice"),
        ("ALEX", "That's my voice. That's the transmission that sent me here.", "plain"),
        ("ALEX", "The unknown signal has been broadcasting for seventeen years, from tonight. It's me. I am the signal.", "plain"),
        ("ELIAS (LIVE)", "Now you understand. The chamber is sealed with the date it all began. The station wrote it down in three places, one in each layer. Come to me, Alex.", "radio")]},
    "c4end": {"lines": [
        ("ALEX", "I have to see what's in that chamber.", "plain")]},
    "c5start": {"lines": [
        ("ALEX", "Everything leads to one room. Whatever I decide, it ends tonight.", "plain")]},
    "chamber_evt": {"lines": [
        ("ALEX", "The door's open. Whatever is inside has been waiting seventeen years.", "plain")]},
    "purpose_evt": {"lines": [
        ("ALEX", "It was never meant to listen. It was built to speak.", "plain"),
        ("ALEX", "And Elias's notes say how to send the last transmission: the unknown first, then the present, then the past.", "plain")]},
    "final_evt": {"lines": [
        ("ALEX", "It's the message from the beginning. Word for word. I'm the one who sends it.", "plain"),
        ("ALEX", "Now I only have to decide what to say.", "plain")]},
}
for _n in range(1, 6):
    EVENTS[f"card{_n}"] = {"card": _n}


# ---------------------------------------------------------------- manager
class StoryManager:
    """Evaluates the story from gp.flags each frame and feeds gp.events."""

    def __init__(self, gp):
        self.gp = gp

    # -- queries --
    def chapter(self):
        f = self.gp.flags
        for c in CHAPTERS:
            if f"ch{c.n}" in f and f"ch{c.n}_done" not in f:
                return c
        return CHAPTERS[-1]

    def mission(self):
        f = self.gp.flags
        c = self.chapter()
        for m in c.missions:
            if "m_" + m.id not in f:
                return m
        return None

    def objective_text(self):
        c, m = self.chapter(), self.mission()
        if m is None:
            return f"CH{c.n}  {c.title.title()}"
        return f"CH{c.n}  {m.text}"

    def hint_text(self):
        m = self.mission()
        if not m:
            return ""
        return m.hint(self.gp) if callable(m.hint) else m.hint

    def chapter_done(self, n):
        return f"ch{n}_done" in self.gp.flags

    # -- progression --
    def update(self):
        gp = self.gp
        f = gp.flags
        f.add("ch1")
        for c in CHAPTERS:
            n = c.n
            if f"ch{n}" not in f:
                break
            if f"ch{n}_done" in f:
                continue
            for m in c.missions:
                if "m_" + m.id in f:
                    continue
                if m.done(gp):
                    f.add("m_" + m.id)
                    gp.on_mission_done(m)
                else:
                    break
            else:
                f.add(f"ch{n}_done")
                if n < 5:
                    f.add(f"ch{n + 1}")
                gp.on_chapter_done(c)
            break
        # make sure every event that should have played is queued (also after loading a save)
        for eid in self.expected_events():
            if "evt_" + eid not in f and eid not in gp.events and eid != gp.current_event:
                gp.events.append(eid)

    def expected_events(self):
        f = self.gp.flags
        out = []
        for c in CHAPTERS:
            if f"ch{c.n}" not in f:
                break
            out += c.start_events[:1] if c.start_events else []
            if c.n == 1 or f"ch{c.n}" in f:
                out += c.start_events[1:]
            for m in c.missions:
                if "m_" + m.id in f and m.event:
                    out.append(m.event)
            if f"ch{c.n}_done" in f and c.end_event:
                out.append(c.end_event)
        return out
