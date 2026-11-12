"""Key bindings. Each action has a primary key you can rebind (Settings > Controls). Movement also always accepts the arrow keys.

Bindings are stored in settings["keys"] as {action: key code}; only changed actions are stored.
"""
from PyQt6.QtCore import Qt

K = Qt.Key
# (action, label, default primary key, keys that always work too)
ACTIONS = [
    ("up", "Move up", K.Key_W, (K.Key_Up,)),
    ("down", "Move down", K.Key_S, (K.Key_Down,)),
    ("left", "Move left", K.Key_A, (K.Key_Left,)),
    ("right", "Move right", K.Key_D, (K.Key_Right,)),
    ("interact", "Interact", K.Key_E, ()),
    ("radio", "Radio on / off", K.Key_Space, ()),
    ("tune", "Change frequency", K.Key_Q, ()),
    ("echo", "Echo Receiver", K.Key_R, ()),
    ("journal", "Journal", K.Key_J, ()),
    ("hint", "Hint", K.Key_K, ()),
    ("guide", "Guide arrows", K.Key_H, ()),
    ("torch", "Flashlight", K.Key_F, ()),
]
DEFAULT = {a: int(k) for a, _l, k, _alt in ACTIONS}
ALT = {a: tuple(int(x) for x in alt) for a, _l, _k, alt in ACTIONS}
LABEL = {a: l for a, l, _k, _alt in ACTIONS}


def key_name(k):
    k = int(k)
    return "SPACE" if k == int(K.Key_Space) else chr(k) if 0x20 < k < 0x7F else "?"


class Keymap:
    def __init__(self, settings):
        self.settings = settings

    def _store(self):
        return self.settings.setdefault("keys", {})

    def primary(self, action):
        return int(self._store().get(action, DEFAULT[action]))

    def keys_for(self, action):
        return {self.primary(action), *ALT[action]}

    def action(self, key):
        """Which action a pressed key triggers (None if unbound)."""
        key = int(key)
        for a, *_ in ACTIONS:
            if key in self.keys_for(a):
                return a
        return None

    def name(self, action):
        return key_name(self.primary(action))

    def allowed(self, key):
        key = int(key)
        reserved = {int(K.Key_Up), int(K.Key_Down), int(K.Key_Left), int(K.Key_Right)}
        return 0x20 <= key < 0x7F and key not in reserved

    def rebind(self, action, key):
        """Bind `key` to `action`. If another action already uses it, the two swap keys. Returns (ok, message)."""
        key = int(key)
        if not self.allowed(key):
            return False, "That key can't be used."
        old = self.primary(action)
        for other, *_ in ACTIONS:
            if other != action and self.primary(other) == key:
                self._store()[other] = old                     # swap, so nothing is left unbound
                self._store()[action] = key
                return True, f"{LABEL[other]} now uses {key_name(old)}."
        self._store()[action] = key
        return True, ""

    def reset(self):
        self.settings["keys"] = {}
