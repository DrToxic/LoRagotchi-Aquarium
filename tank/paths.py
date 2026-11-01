"""Default storage paths for a source checkout of LoRagotchi-Aquarium."""
from pathlib import Path

AQUARIUM_DIR = Path(__file__).resolve().parents[1]
LOCAL_DATA_DIR = AQUARIUM_DIR / ".local"
DEFAULT_SETTINGS_PATH = LOCAL_DATA_DIR / "settings.json"