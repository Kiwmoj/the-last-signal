"""Achievements: checked against the game state a couple of times a second, saved globally (shared by all save slots)."""
from .story import TERMINAL, CHAMBER_FILES

# (id, title, description, check(gp))
ACHIEVEMENTS = [
    ("first_contact", "First Contact", "Pick up the Echo Receiver.", lambda gp: "echo_found" in gp.flags),
    ("tuned_in", "Tuned In", "Change frequency for the first time.", lambda gp: "tuned" in gp.flags),
    ("echo_hunter", "Echo Hunter", "Lock onto four hidden signals.", lambda gp: sum(1 for f in gp.flags if f.startswith("src_")) >= 4),
    ("lights_on", "Let There Be Light", "Restore power to the transmitter.", lambda gp: "fixed" in gp.flags),
    ("open_sesame", "Open Sesame", "Open the research wing.", lambda gp: "door_open" in gp.flags),
    ("archivist", "Archivist", "Unlock the archive.", lambda gp: "archive_open" in gp.flags),
    ("combination", "Combination Master", "Open Staff Locker 2-A.", lambda gp: "locker_open" in gp.flags),
    ("nora", "Nora's Secret", "Open the Wing Safe.", lambda gp: "safe_open" in gp.flags),
    ("calibrated", "Perfect Pitch", "Calibrate the Archive console.", lambda gp: "cal_done" in gp.flags),
    ("secret_end", "The Third Way", "Reach the secret ending.", lambda gp: "decision_echo" in gp.flags),
    ("the_voice", "The Voice Was Yours", "Play recording 09-A.", lambda gp: "revealed" in gp.flags),
    ("chamber", "Into the Chamber", "Open the transmission chamber.", lambda gp: "chamber_open" in gp.flags),
    ("decision", "The Last Decision", "Reach an ending.", lambda gp: "decision" in gp.flags),
    ("two_roads", "Two Roads", "See both endings.", lambda gp: {"warn", "silence"} <= set(gp.game.save.data.get("endings", []))),
    ("every_secret", "Every Secret", "Find Elias's letter and Nora's letter.",
     lambda gp: gp.journal.has("elias_letter") and gp.journal.has("nora_letter")),
    ("reader", "Station Historian", "Read every file on every terminal.",
     lambda gp: all(("file:" + f[0]) in gp.read for d in (TERMINAL, CHAMBER_FILES) for fl in d.values() for f in fl)),
]
TOTAL = len(ACHIEVEMENTS)


def check(gp):
    """Unlock anything newly earned. Returns the list of newly unlocked (id, title)."""
    have = gp.game.save.data.setdefault("achievements", [])
    new = []
    for aid, title, _desc, test in ACHIEVEMENTS:
        if aid not in have:
            try:
                ok = test(gp)
            except Exception:
                ok = False
            if ok:
                have.append(aid)
                new.append((aid, title))
    return new


def completion(save):
    """Percentage 0-100 of achievements unlocked."""
    return int(100 * len(set(save.data.get("achievements", [])) & {a[0] for a in ACHIEVEMENTS}) / TOTAL)
