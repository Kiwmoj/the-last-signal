"""Journal data: discovered clues and keys. Serialised into the save file."""


class Journal:
    def __init__(self, entries=None):
        self.entries = list(entries or [])

    def add(self, eid, title, text, cat="clue"):
        """Add an entry once. Returns True if it is new."""
        if any(e["id"] == eid for e in self.entries):
            return False
        self.entries.append({"id": eid, "title": title, "text": text, "cat": cat})
        return True

    def add_tuple(self, c):
        return self.add(c[0], c[1], c[2], c[3] if len(c) > 3 else "clue")

    def has(self, eid):
        return any(e["id"] == eid for e in self.entries)

    def by_cat(self, cat):
        return [e for e in self.entries if e["cat"] == cat]

    def __len__(self):
        return len(self.entries)

    def to_list(self):
        return [dict(e) for e in self.entries]
