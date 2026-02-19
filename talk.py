# talk.py (SAFE STUB)
# - This tiny stub avoids rare Streamlit Cloud parsing/encoding issues on large scripts.
# - It simply executes talk_impl.py in the same folder.

from __future__ import annotations
from pathlib import Path
import runpy
import sys

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

runpy.run_path(str(BASE_DIR / "talk_impl.py"), run_name="__main__")
