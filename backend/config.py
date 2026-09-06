import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
DB_PATH = Path(os.environ.get("HAZARDMAP_DB", ROOT / "hazardmap.db"))

AI_KEY = os.environ.get("HAZARDMAP_AI_KEY", "").strip()
AI_MODEL = os.environ.get("HAZARDMAP_AI_MODEL", "gpt-4o-mini").strip()
AI_BASE_URL = os.environ.get("HAZARDMAP_AI_BASE_URL", "https://api.openai.com/v1").strip()
AI_TIMEOUT_SECONDS = float(os.environ.get("HAZARDMAP_AI_TIMEOUT", "20"))

MAP_CENTER = (47.6155, -122.3410)
MAP_ZOOM = 14
# a few meters from the seeded fallen-tree cluster so the live demo joins it
DEMO_PIN = (47.62058, -122.34948)

CONFIDENCE_CEILING = 0.97
CONFIDENCE_FLOOR = 0.15
SINGLE_REPORT_CEILING = 0.72
# keep one confident reading from eating the whole score
BASE_DAMPING = 0.6
CORROBORATION_BONUS = 0.52
CORROBORATION_DECAY = 0.74
PHOTO_BONUS = 0.26
PHOTO_EXTRA_BONUS = 0.06
TIGHT_CLUSTER_BONUS = 0.24
AGREEMENT_BONUS = 0.20
DISAGREEMENT_PENALTY = 0.45
RECENCY_MAX_PENALTY = 0.9
