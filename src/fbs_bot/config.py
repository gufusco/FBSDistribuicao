from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
load_dotenv(ROOT / ".env")
VALOR_HORA_ESTADIA = float(os.getenv("VALOR_HORA_ESTADIA", "60"))
MODEL_PATH = MODELS_DIR / "intent_model.joblib"
FALLBACK_THRESHOLD = 0.55
