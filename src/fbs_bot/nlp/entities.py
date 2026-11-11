import re
from rapidfuzz.fuzz import ratio

EMBARQUE_RE = re.compile(r"\bEMB\d{6}\b", re.I)
PLATE_RE = re.compile(r"\b(?:[A-Z]{3}[- ]?\d{4}|[A-Z]{3}[- ]?\d[A-Z]\d{2})\b", re.I)
NF_RE = re.compile(r"\b\d{6,9}\b")

def extract_entities(text):
    return {
        "embarque": (EMBARQUE_RE.search(text) or [None])[0],
        "placa": (PLATE_RE.search(text) or [None])[0],
        "nf": (NF_RE.search(text) or [None])[0],
    }

def find_carriers(text, carriers, threshold=80):
    scored = sorted(((c, ratio(text.lower(), c.lower())) for c in carriers), key=lambda x: x[1], reverse=True)
    return [c for c, score in scored if score >= threshold]
