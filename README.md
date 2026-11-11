# THE LAST SIGNAL

A 2D pixel-art radio-mystery adventure written in Python with PyQt6 and QPainter. All graphics and audio are generated procedurally, so there are no asset files.

You are Alex Reyes, a radio technician sent to the abandoned Station 09 in August 1997. The station has been silent for 17 years, yet something is transmitting tonight. Tune between three frequencies, use the Echo Receiver, solve puzzles across five chapters, and choose how the story ends (two endings).

## Run

```
pip install PyQt6
python main.py
```

Requires Windows or any platform where PyQt6 runs, and Python 3.10+.

## Controls

| Key | Action |
| --- | --- |
| WASD / arrows | Move |
| E | Interact |
| SPACE | Radio on/off |
| Q | Change frequency (88.1 / 104.7 / 121.3 MHz) |
| R | Echo Receiver |
| J | Journal |
| ESC | Pause |

## Custom music

The soundtrack is generated the first time you play (about 20 seconds, in the background). To use your own music, put WAV files named `menu`, `control`, `explore`, `unknown`, `revelation` or `chapter` in a `music/` folder, for example `music/menu.wav`.

## Debug overlay

Start with `TLS_DEBUG=1` and press F3 in game to show chapter, mission and progression state.
