Hotena Full Build (MONOLITHIC talk.py)

Fixes:
- theme_hotena.py provides apply_hotena_theme() + apply_theme() alias to prevent crashes.
- Talk page:
  * options(choices) cached per qid -> no reshuffle when clicking.
  * auto TTS once after submit.
  * waveform recorder (no server storage).
- Theme injected safely into home/words/kanji/mypage/talk (does not touch floating menu logic).

Deploy:
- Main file: home.py
