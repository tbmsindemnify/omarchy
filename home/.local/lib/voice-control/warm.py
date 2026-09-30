"""Load the small command model once per login; no audio or background inference."""
import json
from pathlib import Path
from semantic import interpret
commands=json.loads(Path(__file__).with_name('catalog.json').read_text())
interpret('Cancel',commands,timeout=120)
