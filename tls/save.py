"""Save/load of settings, progress (three save slots), endings and achievements as JSON in the user's home folder."""
import json
import os

PATH = os.path.join(os.path.expanduser("~"), ".the_last_signal.json")
SLOTS = 3

DEFAULTS = {
    "settings": {"music_volume": 6, "sfx_volume": 7, "scanlines": True, "fullscreen": False, "guide_arrows": True, "keys": {}},
    "progress": None,           # always mirrors the ACTIVE slot, so the rest of the game just reads/writes this
    "slots": [None] * SLOTS,
    "slot": 0,
    "endings": [],
    "achievements": [],
}


class SaveData:
    def __init__(self):
        self.data = json.loads(json.dumps(DEFAULTS))
        self.load()

    def load(self):
        try:
            with open(PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return  # first run or corrupt file: keep defaults
        saved = d.get("settings", {})
        if "sfx_volume" not in saved and "volume" in saved:
            saved["sfx_volume"] = saved["volume"]       # older saves had one master volume
        saved.pop("volume", None)
        self.data["settings"].update(saved)
        slots = d.get("slots")
        if isinstance(slots, list):
            self.data["slots"] = (slots + [None] * SLOTS)[:SLOTS]
        elif d.get("progress"):
            self.data["slots"][0] = d["progress"]       # older single-save file becomes slot 1
        slot = d.get("slot", 0)
        self.data["slot"] = slot if isinstance(slot, int) and 0 <= slot < SLOTS else 0
        self.data["progress"] = self.data["slots"][self.data["slot"]]
        self.data["endings"] = list(d.get("endings", []))
        self.data["achievements"] = list(d.get("achievements", []))

    def save(self):
        try:
            with open(PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except OSError:
            pass

    # ---- slots ----
    def set_progress(self, prog):
        """Store progress in the active slot (and mirror it in data['progress'])."""
        self.data["progress"] = prog
        self.data["slots"][self.data["slot"]] = prog

    def select_slot(self, i):
        self.data["slot"] = i
        self.data["progress"] = self.data["slots"][i]

    def clear_slot(self, i):
        self.data["slots"][i] = None
        if self.data["slot"] == i:
            self.data["progress"] = None

    def has_any_save(self):
        return any(s and s.get("v") == 2 for s in self.data["slots"])

    @property
    def settings(self):
        return self.data["settings"]
