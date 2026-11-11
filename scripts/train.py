import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import pandas as pd
from fbs_bot.config import MODEL_PATH, DATA_DIR
from fbs_bot.nlp.classifier import train_model
df=pd.read_csv(DATA_DIR/"corpus_dev.csv"); train_model(df.text,df.label,MODEL_PATH); print("Modelo treinado:",MODEL_PATH)
