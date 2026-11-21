import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fbs_bot.config import DATA_DIR, MODEL_PATH
from fbs_bot.nlp.training import select_model


def main():
    development = pd.read_csv(DATA_DIR / "corpus_dev.csv")
    selection = select_model(development)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(selection.best_model, MODEL_PATH)
    print(f"Modelo selecionado por CV F1-macro: {selection.best_name}")
    print(f"Modelo salvo em {MODEL_PATH}")


if __name__ == "__main__":
    main()
