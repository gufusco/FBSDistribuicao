import re
from unidecode import unidecode

def preprocess(text: str) -> str:
    text = unidecode(str(text)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text)).strip()
