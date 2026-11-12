"""Original procedural soundtrack for THE LAST SIGNAL (no samples, no copyrighted material).

Six moods are synthesised from sine/saw oscillators, filtered noise and slow envelopes:
  menu, control, explore, unknown, revelation  - seamless loops
  chapter                                       - a one-shot cinematic stinger

Run by the game in a separate process (so the UI never stalls):  python -m tls.musicgen <output folder>
Each loop is generated a little longer than its length and the tail is cross-faded over the head, so the
wrap-around point has no click. Files are written to <name>.tmp and renamed, so a half-written file is never loaded.
"""
import array
import math
import os
import random
import sys
import wave

RATE = 11025
TAU = 2 * math.pi
sin = math.sin


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def snap(f, length):
    """Round a frequency so it completes a whole number of cycles in `length` seconds (keeps loops phase-aligned)."""
    return max(1, round(f * length)) / length


def _loop(buf, length, xf):
    n = int(length * RATE)
    x = int(xf * RATE)
    out = buf[:n]
    for i in range(x):
        w = i / x
        out[i] = buf[i] * w + buf[n + i] * (1 - w)
    return out


def _pluck(d, f, amp, decay):
    if d < 0 or d > 5.0 / decay:
        return 0.0
    return amp * math.exp(-d * decay) * (sin(TAU * f * d) + .3 * sin(TAU * f * 2.01 * d))


def _events(seed, scale, n, density):
    """A looping melody: n steps, each either a note from `scale` (MIDI numbers) or a rest. Seeded, so it is always the same tune."""
    rnd = random.Random(seed)
    return [hz(rnd.choice(scale)) if rnd.random() < density else None for _ in range(n)]


def _mel(t, ev, length, amp, decay=1.6):
    """Sum of the melody notes still ringing at time t (each note echoes twice). Wraps at `length`, so loops stay seamless."""
    step = length / len(ev)
    i = int(t / step)
    out = 0.0
    for k in (i, i - 1, i - 2):
        f = ev[k % len(ev)]
        if f:
            d = t - k * step
            out += _pluck(d, f, amp, decay) + _pluck(d - .45, f, amp * .45, decay) + _pluck(d - .9, f, amp * .2, decay)
    return out


def menu():
    L, xf = 40.0, 1.5
    mel = _events(101, [69, 72, 74, 76, 79, 81], 20, .55)           # slow A-minor-pentatonic tune
    n = int((L + xf) * RATE)
    f = [snap(x, L) for x in (55, 110, 164.81, 261.63, 329.63)]
    bells = [(3.0, hz(76)), (8.5, hz(69)), (13.0, hz(72)), (17.5, hz(71)), (21.0, hz(64))]
    rnd = random.Random(11)
    nz = 0.0
    buf = []
    for i in range(n):
        t = i / RATE
        s1 = .5 + .5 * sin(TAU * t / L)
        s2 = .5 + .5 * sin(TAU * 2 * t / L + 1.3)
        v = (.30 * sin(TAU * f[0] * t) + .15 * sin(TAU * f[1] * t) * (.4 + .6 * s1)
             + .09 * sin(TAU * (f[1] + 3 / L) * t) * s2
             + .11 * sin(TAU * f[2] * t) * s2 + .08 * sin(TAU * f[3] * t) * (1 - s2) + .05 * sin(TAU * f[4] * t) * s1)
        for bt, bf in bells:
            v += _pluck(t - bt, bf, .11, 1.5) + _pluck(t - bt - .75, bf, .05, 1.8)
        v += _mel(t, mel, L, .07, 1.2)
        nz += (rnd.uniform(-1, 1) - nz) * .22                   # distant radio static
        v += nz * .03 * (.3 + .7 * s2)
        for pt in (6.0, 18.0, 30.0):                            # occasional electronic pulse
            d = t - pt
            if 0 <= d < 1.5:
                v += .10 * sin(TAU * 45 * d) * math.exp(-d * 3)
        buf.append(v)
    return _loop(buf, L, xf)


def control():
    L, xf = 32.0, 1.0
    mel = _events(202, [62, 65, 69, 72, 74], 8, .4)                  # sparse, distant notes
    n = int((L + xf) * RATE)
    rnd = random.Random(23)
    events = [(rnd.uniform(0, L), rnd.uniform(.08, .35), rnd.uniform(900, 2600)) for _ in range(13)]
    pad = [snap(x, L) for x in (146.83, 174.61, 220.0)]
    base = snap(55, L)
    crk = 0.0
    buf = []
    for i in range(n):
        t = i / RATE
        s1 = .5 + .5 * sin(TAU * t / L)
        v = .22 * sin(TAU * base * t) + .07 * sin(TAU * snap(82.5, L) * t) * s1
        v += .05 * sin(TAU * 60 * t) + .03 * sin(TAU * 120 * t) + .015 * sin(TAU * 180 * t)        # mains hum
        v += .05 * s1 * (sin(TAU * pad[0] * t) + sin(TAU * pad[1] * t) * .8) + .04 * (1 - s1) * sin(TAU * pad[2] * t)
        for (st, du, fr) in events:                                                                  # radio interference
            d = t - st
            if 0 <= d < du:
                v += .06 * rnd.uniform(-1, 1) * sin(math.pi * d / du) * (.5 + .5 * sin(TAU * fr * t))
        if rnd.random() < .0004:
            crk = rnd.uniform(-.25, .25)
        v += crk + _mel(t, mel, L, .035, 1.0)
        crk *= .88
        for bt in (4.0, 13.5):
            d = t - bt
            if 0 <= d < .05 or 0 <= d - .12 < .05:
                v += .05 * sin(TAU * 1320 * t)
        for k in range(6):
            d = t - 5.0 * k
            if 0 <= d < 1.2:
                v += .08 * sin(TAU * 60 * d) * math.exp(-d * 4)
        buf.append(v)
    return _loop(buf, L, xf)


def explore():
    L, xf = 56.0, 1.5
    mel = _events(303, [69, 72, 74, 76, 77, 81, 84], 28, .6)
    n = int((L + xf) * RATE)
    chords = [(45, [57, 60, 64]), (41, [53, 57, 60, 64]), (38, [50, 53, 57, 62]), (40, [52, 56, 59, 64])]
    pattern = [0, 2, 1, 3, 2, 1, 0, 2]
    hop = L / 4
    buf = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        for k, (root, notes) in enumerate(chords):
            d = ((t - (k + .5) * hop + L / 2) % L) - L / 2
            if abs(d) >= hop:
                continue
            w = .5 + .5 * math.cos(math.pi * d / hop)
            v += w * .13 * sin(TAU * snap(hz(root), L) * t)
            for nn in notes:
                fr = snap(hz(nn), L)
                v += w * .045 * (sin(TAU * fr * t) + sin(TAU * (fr + 2 / L) * t))
        step = int(t / 1.75)
        for st in (step, step - 1):
            d = t - st * 1.75
            ci = int(((st * 1.75) % L) / hop) % 4
            tones = chords[ci][1]
            note = tones[pattern[st % 8] % len(tones)] + 12
            v += _pluck(d, hz(note), .05, 2.2) + _pluck(d - .875, hz(note), .025, 2.4)
        v += _mel(t, mel, L, .045, 1.5)
        d = t % 3.5
        v += .11 * sin(TAU * 50 * d) * math.exp(-d * 5)
        buf.append(v)
    return _loop(buf, L, xf)


def unknown():
    L, xf = 24.0, 1.5
    mel = _events(404, [66, 69, 70, 75, 78], 12, .45)                 # odd, unresolved tune
    n = int((L + xf) * RATE)
    rnd = random.Random(7)
    a, b = snap(110, L), snap(116.54, L)             # a minor second: slow, uneasy beating
    ring_c, ring_m = snap(220, L), snap(3.7, L)
    hold, c = 0.0, 0
    buf = []
    for i in range(n):
        t = i / RATE
        s1 = .5 + .5 * sin(TAU * 3 * t / L)
        v = .2 * sin(TAU * a * t) + .18 * sin(TAU * b * t)
        v += .09 * sin(TAU * snap(146.83, L) * t) * (.6 + .4 * sin(TAU * 7 * t)) + .07 * sin(TAU * snap(207.65, L) * t) * (.6 + .4 * sin(TAU * 7 * t + 1))
        v += .10 * sin(TAU * ring_c * t) * sin(TAU * ring_m * t)
        for gt in (5.0, 15.0):                         # falling glissando, like a tape slowing down
            d = t - gt
            if 0 <= d < 4.0:
                v += .09 * sin(math.pi * d / 4.0) * sin(TAU * 880 * (1 - math.exp(-.35 * d)) / .35)
        d = t - 18.0
        if d >= 0:
            v += .10 * (d / 6.0) ** 2 * sin(TAU * snap(330, L) * t)
        v += _mel(t, mel, L, .05, 1.1)
        if c % 6 == 0:                                 # bit-crushed hiss
            hold = rnd.uniform(-1, 1)
        c += 1
        v += hold * .03 * (.3 + .7 * s1)
        buf.append(math.tanh(v * 2.2) * .45)
    return _loop(buf, L, xf)


def revelation():
    L, xf = 20.0, 1.0
    mel = _events(505, [57, 60, 63, 64, 67], 10, .5)
    n = int((L + xf) * RATE)
    notes = [snap(x, L) for x in (110, 164.81, 261.63)]
    bb = snap(233.08, L)
    rnd = random.Random(31)
    nz = 0.0
    buf = []
    for i in range(n):
        t = i / RATE
        swell = .4 + .6 * (.5 - .5 * math.cos(TAU * t / L))
        wb = max(0.0, sin(math.pi * (t % L) / L)) ** 2          # the tense semitone creeps in mid-loop
        v = 0.0
        for fr in notes:
            v += .05 * swell * (sin(TAU * fr * t) + sin(TAU * 2 * fr * t) / 2 + sin(TAU * 3 * fr * t) / 3)
        v += .06 * swell * wb * (sin(TAU * bb * t) + sin(TAU * 2 * bb * t) / 2)
        d = t % 1.25                                          # heartbeat: lub-dub
        v += .22 * sin(TAU * 48 * d) * math.exp(-d * 9) + .15 * sin(TAU * 55 * (d - .32)) * math.exp(-(d - .32) * 10) * (1 if d >= .32 else 0)
        for pt, fr in ((5.0, 1760.0), (13.0, 1480.0)):
            v += _pluck(t - pt, fr, .05, 1.6)
        v += _mel(t, mel, L, .045, 1.3)
        nz += (rnd.uniform(-1, 1) - nz) * .1
        v += nz * .04 * swell
        buf.append(v)
    return _loop(buf, L, xf)


def chapter():
    L = 6.0
    n = int(L * RATE)
    rnd = random.Random(5)
    nz = 0.0
    buf = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        if t < 2.2:                                           # rising swell into the hit
            u = t / 2.2
            v += .22 * u * u * sin(TAU * (80 * t + 320 / (2 * 2.2) * t * t))
            nz += (rnd.uniform(-1, 1) - nz) * .2
            v += .10 * u * u * nz
        else:
            d = t - 2.2
            v += .55 * sin(TAU * 45 * d) * math.exp(-d * 1.4)
            nz += (rnd.uniform(-1, 1) - nz) * .3
            v += .25 * nz * math.exp(-d * 9)
            for k, m in enumerate((57, 64, 69, 72)):
                v += _pluck(d - .1 * k, hz(m), .09, 1.1) + _pluck(d - .1 * k - .5, hz(m), .04, 1.3)
        v *= min(1.0, (L - t) / 1.2)
        buf.append(v)
    return buf


TRACKS = (("menu", menu), ("control", control), ("explore", explore), ("unknown", unknown), ("revelation", revelation), ("chapter", chapter))


# ======================================================================================================================
# Calm piano soundtrack (the one the game uses). Soft piano notes, long silences and a little echo, all original.
# Every note is written straight into a buffer of exactly the loop length and wraps around its end, so loops are seamless.
# ======================================================================================================================
def _piano_into(buf, t0, midi, amp, dur=4.0, detune=0.0):
    n = len(buf)
    f = hz(midi) * (1 + detune)
    i0 = int(t0 * RATE)
    for k in range(int(dur * RATE)):
        d = k / RATE
        att = min(1.0, d * 120)
        e = math.exp(-d * 1.1)
        v = (sin(TAU * f * d) * e + .38 * sin(TAU * 2 * f * d) * math.exp(-d * 2.0) + .14 * sin(TAU * 3.01 * f * d) * math.exp(-d * 3.4)) * att
        buf[(i0 + k) % n] += v * amp


def _note(buf, t, midi, amp, echo=True, detune=0.0):
    _piano_into(buf, t, midi, amp, 4.0, detune)
    if echo:                                                   # a soft room echo
        _piano_into(buf, t + .55, midi, amp * .30, 2.4, detune)
        _piano_into(buf, t + 1.15, midi, amp * .12, 1.6, detune)


def _calm(L, bars, chords, scale, seed, density=.6, melody=.5, amp=.16, bass=True, detune=0.0, hiss=.0, drone=None):
    buf = [0.0] * int(L * RATE)
    rnd = random.Random(seed)
    bar = L / bars
    for b in range(bars):
        chord = chords[b % len(chords)]
        t = b * bar
        if bass:
            _note(buf, t + rnd.uniform(0, .1), chord[0] - 12, amp * .9, True, detune)
        for i, nn in enumerate(chord[1:]):
            if rnd.random() < density:
                _note(buf, t + .5 + i * bar * .22 + rnd.uniform(0, .15), nn, amp * rnd.uniform(.55, .85), True, detune)
        if rnd.random() < melody:
            _note(buf, t + bar * rnd.uniform(.35, .8), rnd.choice(scale) + 12, amp * .75, True, detune)
    if drone:                                                   # a very quiet held tone under the piano
        fd = snap(hz(drone), L)
        for i in range(len(buf)):
            buf[i] += .03 * sin(TAU * fd * i / RATE)
    if hiss:
        nz = 0.0
        for i in range(len(buf)):
            nz += (rnd.uniform(-1, 1) - nz) * .15
            buf[i] += nz * hiss
    return buf


def menu():                                                    # warm and open, C major
    return _calm(48.0, 12, [[48, 60, 64, 67, 71], [45, 57, 60, 64, 67], [41, 53, 57, 60, 64], [43, 55, 59, 62, 65]],
                 [72, 74, 76, 79, 81], 11, density=.65, melody=.6, amp=.16, drone=36)


def control():                                                 # quieter and lower, with distant radio hiss
    return _calm(40.0, 10, [[38, 50, 53, 57], [34, 46, 50, 53], [36, 48, 52, 55], [31, 43, 47, 50]],
                 [62, 65, 67, 69, 72], 22, density=.45, melody=.4, amp=.13, hiss=.012, drone=26)


def explore():                                                 # gentle and curious, A minor into F
    return _calm(56.0, 14, [[45, 57, 60, 64, 67], [41, 53, 57, 60, 64], [48, 60, 64, 67, 71], [43, 55, 59, 62, 67]],
                 [69, 72, 74, 76, 79, 81], 33, density=.7, melody=.7, amp=.15, drone=33)


def unknown():                                                 # the same piano, a little out of tune, with an unresolved note
    return _calm(32.0, 8, [[45, 57, 60, 66], [42, 54, 57, 63], [46, 58, 62, 68], [40, 52, 56, 62]],
                 [66, 69, 70, 75, 78], 44, density=.55, melody=.7, amp=.14, detune=.012, hiss=.01, drone=33)


def revelation():                                              # slow and weighty, low piano under a held note
    return _calm(24.0, 6, [[36, 48, 51, 55, 58], [32, 44, 48, 51, 55], [34, 46, 50, 53, 57]],
                 [60, 63, 65, 67, 70], 55, density=.5, melody=.6, amp=.17, drone=24)


TRACKS = (("menu", menu), ("control", control), ("explore", explore), ("unknown", unknown), ("revelation", revelation), ("chapter", chapter))


def write(path, samples):
    peak = max(1e-6, max(abs(s) for s in samples))
    rms = math.sqrt(sum(s * s for s in samples) / len(samples)) or 1e-6
    g = min(.85 / peak, .2 / rms)                 # every track ends up at a similar, moderate loudness
    data = array.array("h", (int(max(-1.0, min(1.0, s * g)) * 32000) for s in samples))
    tmp = path + ".tmp"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    os.replace(tmp, path)


def main(folder):
    os.makedirs(folder, exist_ok=True)
    for name, fn in TRACKS:
        path = os.path.join(folder, name + ".wav")
        if not os.path.exists(path):
            write(path, fn())


if __name__ == "__main__":
    main(sys.argv[1])
