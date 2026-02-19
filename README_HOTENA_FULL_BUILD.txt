Hotena - Full Build (baseline: hotena_hub_v14_talk_recording_design_A)

Included fixes:
- Talk page: SAFE STUB (talk.py) + talk_impl.py to avoid Streamlit Cloud _get_code_from_file errors.
- Talk choices fixed: choices cached per qid so options do not reshuffle on every click.
- Talk: Auto TTS once after submit + waveform recorder (no server storage).
- Theme: theme_hotena.py injected lightly into home/words/kanji/mypage (does not modify floating menu).

Deploy:
- Main file: home.py
