Hotena SFX patch (centralized)
- core.py: adds play_sfx_once(key, name)
- app.py, hotena_basic.py: remove local mp3-based SFX and route to core.py SFX
  - render_sound_toggle(): toggles core.set_sfx_enabled and keeps sound_enabled for compatibility
  - submit SFX: plays once per quiz_version key via core.play_sfx_once

No other logic/UI touched.
