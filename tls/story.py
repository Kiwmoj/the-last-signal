"""All story text and puzzle data for THE LAST SIGNAL (Station 09, August 1997).

BACKSTORY (revealed gradually):
  1980: Dr. Elias Marlowe's team at Station 09 learned that three radio bands carry fragments of time:
        88.1 the present, 104.7 the past, 121.3 a voice that belongs to no moment they could name.
        On the night of the incident (14 Aug 1980, 03:33) the unknown band spoke to them by name.
        Marlowe opened the archive to learn who was speaking, was recorded, and the signal began to loop.
  1997: Alex Reyes is sent to investigate. The unknown voice is Alex's own warning, sent from tonight through
        the final transmitter ("do not open the archive"). The player chooses whether to send a corrected
        warning (rewrite history) or shut the transmitter down.

Journal entry tuples are (id, title, text) or (id, title, text, category).
Categories: "clue" (documents, discoveries), "key" (passwords, codes), "person", "puzzle".
Terminal file lock flags: "flag" = locked until flag set, "+flag" = file only appears once flag set.
"""

# ---------------------------------------------------------------- puzzle constants
PASSWORD = "NORA1971"        # archive door: NAME (decrypted log, 88.1) + YEAR (notebook, 104.7), format hint on 121.3
CHAMBER_CODE = "140880"      # chamber door: DAY (88.1) + MONTH (104.7) + YEAR (121.3) plaques
LOCKER_CODE = "6402"         # optional Staff Locker 2-A: digits on the duty board (104.7), whiteboard (88.1 / 121.3), wing slate (88.1)
SAFE_CODE = "917"            # optional Wing Safe: count what Nora drew. Control Room (104.7) 9 rays, Offices (88.1) 1 tree, Archive (121.3) 7 stars
FRAG_ORDER = [1, 0, 2]       # Old Radio: past fragment, present fragment, unknown fragment
RECEIVER_PULSES = {0: 3, 1: 1, 2: 2}
RECEIVER_ORDER = [0, 2, 1]   # heaviest pulse count first: 88.1 (3), 121.3 (2), 104.7 (1)
FINAL_ORDER = [2, 0, 1]      # final transmitter: the unknown, then the present, then the past
FINAL_LINES = {2: "Station 09... if anyone can hear this...", 0: "...do not open the archive...", 1: "...it knows you're listening."}

# ---------------------------------------------------------------- puzzle tracker (journal tab)
PUZZLES = [
    ("tut_done", "Echo Training",
     "The Echo Receiver detects signals the radio cannot. Open it with R, SCAN to learn which band hides something, "
     "TRACK it down, lock onto the source with E, then replay the recording from MEMORY.",
     "The receiver is yours. Its first recording says the research wing is alive but sealed behind a dead power circuit."),
    ("fixed", "Power the Transmitter",
     "The research wing runs off the main transmitter circuit, and its fuse is gone. The Past remembers where a spare was hidden. "
     "The fuse slot only shows on 104.7.",
     "The transmitter hums and the whole station wakes: lights, relays, and an old radio that begins to whisper."),
    ("door_open", "The Wing Lock",
     "Elias's recording says the research wing door wants three tones: memory, the dark, the present. "
     "Each clue exists on only one frequency.",
     "The research wing door opens."),
    ("p1_done", "The Missing Transmission",
     "The old radio is wired to the research wing relay. The night's emergency transmission survived in three pieces, "
     "one on each frequency. Record them with the Echo Receiver and put them in order.",
     "Elias's emergency transmission is restored and his personal log is decrypted on the terminal."),
    ("archive_open", "The Locked Archive",
     "The archive key is a name and a year. Elias's decrypted log, Dr. Wren's notebook and a file on 121.3 each hold a piece.",
     "The archive is open."),
    ("p3_done", "The Unknown Signal",
     "The archive receiver wakes only when fed three tones in the right order. Read each pulse count on its scope. "
     "The notebook on 121.3 and Wren's whisper give the rule.",
     "The receiver plays Elias's last warning to his team, and then a live voice breaks in."),
    ("final_signal", "The Live Voice",
     "A live voice broke into the recording. Switch on tracking and follow it.",
     "The voice knows your name. It says it has heard yours for seventeen years."),
    ("trail_done", "Follow the Echoes",
     "Elias left three echoes, one per band, in three places: the control room (past), the offices (unknown) and the research wing (present). "
     "Each points to the next.",
     "The trail ends at recording rack 09-A in the archive."),
    ("locker_open", "Staff Locker 2-A",
     "Marlowe's staff locker in the Offices takes a four-digit code. Its digits were left in different rooms: the Control Room duty board, "
     "the Offices whiteboard and the Research Wing slate. Each is only readable on one frequency.",
     "Inside: Elias's unsent letter to his daughter, and a maintenance tape from the night it began."),
    ("safe_open", "The Wing Safe",
     "A small safe in the research wing is marked with a child's handwriting: count what Nora drew. Her three drawings hang in three different rooms, "
     "and each shows its picture clearly on only one frequency.",
     "Inside: a letter from Nora, written the week it began, and her cassette."),
    ("chamber_open", "The Chamber Lock",
     "The chamber opens to the date everything began. The station wrote it in three places, one per layer: the day, the month and the year.",
     "The Transmission Chamber is open."),
    ("final_ready", "The Final Transmission",
     "Elias's notes give the order: begin with the unknown, then the present, then the past. Send each band's tone at the final transmitter.",
     "The final transmission is assembled. It is the message that began your night."),
]
REWARD = {fl: reward for (fl, _t, _h, reward) in PUZZLES}

# ---------------------------------------------------------------- terminal (files differ per frequency)
# each file: (name, lock, text, journal clue or None)
TERMINAL = {
    0: [
        ("STATION_LOG.TXT", None,
         "STATION 09 // OPERATIONS LOG. Final entry, 03:33 AM: 'Unknown band active again. It called Dr. Wren by name. Dr. Marlowe has ordered the "
         "evacuation and is staying behind to close the archive.' The log ends there. The cursor blinks as if waiting for you to reply.",
         ("log_final", "Final station log", "Station 09's last log entry: at 03:33 AM the unknown band called a researcher by name. Dr. Marlowe ordered an evacuation and stayed behind.")),
        ("STAFF.TXT", None,
         "STAFF, STATION 09. Lead researcher: Dr. E. MARLOWE (status: MISSING). Research: Dr. A. WREN (evacuated). Operators: 4 (evacuated). "
         "Visiting family: 1 minor (evacuated). Station status: ABANDONED, 1980.",
         ("staff", "The station staff", "Dr. Elias Marlowe was the lead researcher and is listed as missing. Dr. Ada Wren ran the frequency research. Everyone else was evacuated in 1980.")),
        ("MAINTENANCE.TXT", None,
         "MAINTENANCE NOTE: 104.7 shows the station as it was. 121.3 shows what the station tried to forget. "
         "88.1 is only what remains. The spare fuse was put somewhere safe. Ask the station.",
         ("freq_guide", "Frequency guide", "88.1 THE PRESENT is what remains. 104.7 THE PAST is the station as it was. 121.3 THE UNKNOWN is what it tried to forget.")),
        ("PERSONAL.LOG", "p1_done",
         "[DECRYPTED] Personal log of E. Marlowe. 'Nora visited this week. Nine years old, and she hears the unknown band without a headset. "
         "I locked the archive and used her name and the year she was born as the key, so that no one who did not love her could open it.'",
         ("key_name", "Archive key: the name", "Marlowe's archive key is his daughter's NAME followed by her birth YEAR. Her name is NORA.", "key")),
        ("WING_RELAY.LOG", "+beacon",
         "RELAY LOG: the research wing relay has been reconnected to the control room radio. It has repeated one recording since 03:33, 1980: "
         "the evacuation night's emergency transmission, broken into three fragments, one on each band.",
         ("relay_log", "The wing relay", "The old radio in the control room is wired to the research wing relay, which repeats the night's emergency transmission as three fragments, one per band.")),
        ("INCIDENT.TXT", "+revealed",
         "INCIDENT REPORT: the date of the incident is stamped in three places, one in each layer of the station. The present holds the day. "
         "The past holds the month. The unknown holds the year. The transmission chamber door answers to that date.",
         ("incident_hint", "Incident report", "The chamber door opens to the incident date: the day (88.1, control room), the month (104.7, offices) and the year (121.3, research wing).", "key")),
    ],
    1: [
        ("MAIL_0114.TXT", None,
         "FROM: E. Marlowe  TO: Dr. Wren. 'The east corridor is whole again on 104.7. Spare fuses keep vanishing, and the old hands say the Unknown takes them. "
         "The wing lock takes tones, not numbers: three tones in the right order. The archive receiver will not wake. Did you leave its rule in your notebook?'",
         ("mail_recv", "Marlowe's mail", "The archive receiver will not wake. Dr. Wren's research notebook should hold the activation rule.")),
        ("ORDERS.TXT", None,
         "STANDING ORDERS: Never answer the unknown band alone. Never open the archive while the unknown band is active. "
         "If you hear a voice you recognise, do not reply.",
         ("orders", "Standing orders", "Researchers were ordered never to answer the unknown band alone and never to open the archive while it was active.")),
    ],
    2: [
        ("KEY.FMT", None,
         "ARCHIVE KEY FORMAT: A NAME. THEN A YEAR. CAPITAL LETTERS. NO SPACES. EXAMPLE: ADAM1999.",
         ("key_format", "Archive key: the format", "The archive key is a NAME followed by a YEAR: capital letters, no spaces (for example ADAM1999).", "key")),
        ("WHISPER.DAT", None,
         "Y O U   A R E   L I S T E N I N G.   I T   I S   L I S T E N I N G   B A C K.",
         ("whisper", "The whisper", "On 121.3 the terminal whispers that whoever listens is listened to in return.")),
    ],
}

# Elias's chamber terminal (Chapter 5): the purpose of the experiments
CHAMBER_FILES = {
    0: [("PROJECT_09.TXT", None,
         "PROJECT 09. PURPOSE: to prove that a message can be carried backward across time, so a warning might reach people before it is too late. "
         "Station 09 was never built to listen. It was built to SPEAK.",
         ("purpose", "The purpose of Station 09", "Station 09 was built to carry one warning backward through time. It was built to speak, not to listen.")),
        ],
    1: [("FIRST_MESSAGE.TXT", None,
         "On the night of the incident the first message arrived on the unknown band: a stranger's voice. 'Do not open the archive. It knows you are listening.' "
         "Marlowe did not know who was speaking, so he opened the archive to find out. It recorded him, and the signal began to loop.",
         ("first_message", "The first message", "The first message on the unknown band was a stranger's warning not to open the archive. Marlowe opened it to find the speaker, and the signal began to loop.")),
        ],
    2: [("LOOP.DAT", None,
         "THE VOICE WAS NEVER A STRANGER. IT SPEAKS FROM TONIGHT. IT SENDS FROM THIS CHAMBER, THROUGH THE LAST TRANSMITTER, "
         "IN THE VOICE OF THE ONE WHO FINISHES IT. EVERY LISTENER BECOMES THE SENDER.",
         ("loop", "The loop", "The voice that warned Marlowe speaks from tonight, from this chamber. Whoever finishes the last transmission becomes the sender.")),
        ],
}

# ---------------------------------------------------------------- research notebook (per frequency)
NOTEBOOK = {
    0: (["RESEARCH NOTEBOOK of Dr. A. Wren, Station 09. 'Hypothesis: radio carries more than sound. Each band carries a different layer of the same place. "
         "88.1 is the layer we stand in. 104.7 is the layer behind us, the echoes of moments that have passed. 121.3 belongs to neither.'",
         "'We built the station on this headland because the signal is strongest here. Marlowe keeps saying the unknown band is not noise. It is a voice.'"],
        ("wren_theory", "Wren's theory", "Dr. Wren believed each frequency shows a different layer of one place: 88.1 the present, 104.7 the past, 121.3 something that belongs to neither.")),
    1: (["Past page. 'Marlowe's girl, Nora, visited today. Born in 1971, and already she can hear the unknown band without a headset. "
         "I told him to keep her away from the receiver.'"],
        ("key_year", "Archive key: the year", "Dr. Wren's notebook: Marlowe's daughter Nora was born in 1971. The year of the key is 1971.", "key")),
    2: (["Unknown page. 'The receiver cannot be woken by one tone. It wants all three, the HEAVIEST signal first and the lightest last. "
         "Weight is the number of pulses it sends. Count them on the receiver's scope.'"],
        ("recv_rule", "Receiver rule", "Feed the archive receiver all three tones, heaviest pulse count first, lightest last. Read the counts on its scope.")),
}

# ---------------------------------------------------------------- old radio (research wing relay)
RADIO_FRAGMENTS = {
    1: "This is Dr. Marlowe, Station 09. Three thirty-three in the morning. The unknown band is speaking again.",
    0: "...it knows each of us by name. Wren says we should close the archive. I am going to open it, to hear who is speaking.",
    2: "...if anyone hears this later, do not follow me in. Close the archive, and tell Nora I stayed to listen.",
}
RADIO_VOICES = {   # extra recordings you hear on each band once the message is restored
    0: "Static. Under it, a man humming a lullaby, slightly out of tune.",
    1: "A child's laughter, a door closing, a chair scraping across this very floor.",
    2: "A girl's whisper, very close: 'Dad, I can hear you.'",
}
RADIO_RESTORED = ["Marlowe's personal log on the terminal has been decrypted.",
                  "It says the archive key is built from a name and a year."]

RECEIVER_DECODE = [
    "RECORDING, 03:31 AM. DR. MARLOWE TO ALL STAFF: 'Everyone out, now. Take the children. The unknown band is not noise, and it is not a recording.'",
    "'It is a person, and it has been listening to us the whole time. Do not answer it. Do not open the archive. I will stay and try to shut it down.'",
    "[END OF RECORDING]  Static. Then a live voice breaks through, close and calm: 'Alex. Alex Reyes. You were not supposed to hear this yet.'",
]

# ---------------------------------------------------------------- Echo Receiver
ECHO_PICKUP = [
    "A handheld scanner sits on the side table, warm to the touch: a dial, a small glowing display, three worn buttons, the word ECHO scratched into its casing and the initials E.M. on the back.",
    "It hums softly, as if it has been waiting for you. Press R at any time to open it.",
    "SCAN shows which band hides something near you. TRACK points you to it. MEMORY replays every recording you find.",
]

# Hidden signal sources: invisible and unreachable until the Echo Receiver is tracking AND the radio is on the right band.
# id -> (title, recording lines, journal clue or None). For "tut" the last line is an instruction and is not stored.
SOURCES = {
    "tut": ("Faint Echo", [
        "A faint voice rides the static: 'This is Dr. Elias Marlowe, Station 09. If a receiver is picking this up, the research wing relay is still alive.'",
        "'The wing is sealed from this room and answers only to the main power circuit. The circuit is dead. Restore power first.'",
        "The receiver has stored the recording. Open it with R, choose MEMORY, and replay it."],
        ("echo_tut", "Marlowe's echo", "Dr. Marlowe's echo on 104.7: the research wing is sealed and answers only to the main power circuit, which is dead. Restore power first. "
                                      "Recordings are kept in the Echo Receiver's MEMORY.")),
    "elias": ("Elias's Recording", [
        "The static clears. A tired, kind voice: 'Elias Marlowe. If the power is on, you did what I could not.'",
        "'The wing lock takes three tones, and I built it so that only someone who understands the three layers could pass: first memory, then the dark, then the present.'",
        "'Be careful. It has been listening since the first night.'"],
        ("elias_rec", "Elias's recording", "Elias's recording: the research wing lock takes three tones in the order memory (104.7), the dark (121.3), the present (88.1). "
                                          "'Be careful. It has been listening since the first night.'")),
    "wren": ("Whispering Source", [
        "A dry, tired voice: 'This is Dr. Wren. I counted the pulses at last, and understood too late.'",
        "'The heaviest signal is the one that wants to be heard first. Feed the archive receiver in that order, or it will never wake.'"],
        ("wren_voice", "Wren's whisper", "Dr. Wren's recording on 121.3: the archive receiver must be fed the heaviest pulse count first.")),
    "nora": ("Marlowe's Message", [
        "A man's voice, gentle and close: 'Nora, if you can hear this, Daddy is just in the next frequency.'",
        "'Do not be afraid of the static. It is only the sound of everyone who has ever tried to reach each other.'"],
        ("marlowe_nora", "Marlowe's message to Nora", "A recording on 104.7 in the research wing: Marlowe promising his daughter Nora that he is 'just in the next frequency'.")),
    "final": ("The Live Voice", [
        "The scanner locks. The live voice, close and unhurried: 'Alex Reyes. Technician. I know your name, and I did not think you would come.'",
        "'Your voice has been in my headphones for seventeen years. I did not know whose it was until now.'",
        "'Follow the echoes I left in each room. Start where I last sat. Hurry: the station is starting to remember.'"],
        ("final_signal", "The live voice", "A live voice on 121.3 knows Alex's name and says Alex's voice has been in its headphones for seventeen years. "
                                          "It told Alex to follow its echoes, starting where it last sat: the control room, on 104.7.")),
    "trail1": ("Echo: Control Room", [
        "03:11 AM. Marlowe's voice, hurried: 'The unknown band called Wren by name, and told her what she would say next. She said it, word for word.'",
        "'We named it the Oracle. I want to ask it who it is.'"],
        ("trail1", "Echo: the control room", "03:11 AM. The unknown band called Wren by name and predicted her next words exactly. Marlowe wanted to ask it who it was.")),
    "trail2": ("Echo: Offices", [
        "03:19 AM. Wren, frightened: 'Elias, it is not predicting. It is remembering. It has heard all of this before.'",
        "'And it has Nora's voice in it. And someone else's. A man we have never met.'"],
        ("trail2", "Echo: the offices", "03:19 AM. Wren realised the unknown band is remembering, not predicting. It holds Nora's voice and the voice of a man they have never met.")),
    "trail3": ("Echo: Research Wing", [
        "03:27 AM. Marlowe: 'I asked it who it was. It answered in that stranger's voice: I am the one who will send this. Open the archive and you will hear.'",
        "'So I am going to open the archive. God help me.'"],
        ("trail3", "Echo: the research wing", "03:27 AM. Marlowe asked the unknown band who it was. It said: 'I am the one who will send this. Open the archive and you will hear.' He decided to open it.")),
}

# ---------------------------------------------------------------- the last decision and endings
DECISION_INTRO = ["The message is assembled: the words that began your night. Once sent, they travel back to 1980.",
                  "You know what happened to Elias. You know who the voice is. Only one more thing remains: what to say."]
DECISION = {
    "warn": ("SEND THE WARNING",
             "Add what Elias never knew: who is speaking, and why. He will not open the archive. The station never falls silent. "
             "And the call that brought you here is never made."),
    "silence": ("SHUT IT DOWN",
                "Cut the power. The signal ends after seventeen years. What happened in 1980 stays as it was, "
                "and you walk out with the truth."),
}
ENDINGS = {
    "warn": ("ENDING: THE WARNING", (255, 210, 120), [
        "You key the transmitter and speak what Elias never heard: your name, the date, and the one fact he cannot ignore. 'Nora is safe. Close the archive.'",
        "Seventeen years collapse into a single breath. Somewhere in 1980, a man lowers his hand from a lever.",
        "The station hums. The lights hold. In the control room, the clock moves past 03:33 for the first time.",
        "Alex Reyes was never sent here. The call was never made. But on some quiet night, a technician somewhere hears a voice on a dead channel say: 'Thank you.'"]),
    "silence": ("ENDING: THE SILENCE", (120, 190, 255), [
        "You cut the power to the last transmitter. The coils wind down. The signal that has called for seventeen years finally stops.",
        "'Alex,' says Elias, very faintly, 'tell Nora I stayed to listen.' Then only static.",
        "Dawn finds you at the station gate with a satchel of recordings and a truth no one will believe.",
        "Station 09 is silent. But some nights, tuning the dial between stations, you hear a man humming a lullaby, out of tune. And you hum along."]),
}
CREDITS = [
    ("THE LAST SIGNAL", 0), ("", 0),
    ("CAST", 1), ("Alex Reyes", 2), ("Dr. Elias Marlowe", 2), ("Dr. Ada Wren", 2), ("Nora Marlowe", 2), ("Dispatch", 2), ("", 0),
    ("DESIGN, STORY AND CODE", 1), ("Game jam entry", 2), ("", 0),
    ("BUILT WITH", 1), ("Python", 2), ("PyQt6 and QPainter", 2), ("Every pixel and sound drawn and synthesised in code", 2), ("", 0),
    ("Thank you for listening.", 1),
]
