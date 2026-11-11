"""Save/load of settings and progress as JSON in the user's home folder."""
import json
import os

PATH = os.path.join(os.path.expanduser("~"), ".the_last_signal.json")

DEFAULTS = {
    "settings": {"music_volume": 6, "sfx_volume": 7, "scanlines": True, "fullscreen": False},
    "progress": None,  # filled by gameplay in later stages
}


class SaveData:
    def __init__(self):
        self.data = json.loads(json.dumps(DEFAULTS))
        self.load()

    def load(self):
        try:
            with open(PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            saved = d.get("settings", {})
            if "sfx_volume" not in saved and "volume" in saved:
                saved["sfx_volume"] = saved["volume"]       # older saves had one master volume
            saved.pop("volume", None)
            self.data["settings"].update(saved)
            self.data["progress"] = d.get("progress")
        except (OSError, ValueError):
            pass  # first run or corrupt file: keep defaults

    def save(self):
        try:
            with open(PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except OSError:
            pass

    @property
    def settings(self):
        return self.data["settings"]
