import re

from rapidfuzz.fuzz import partial_ratio, token_set_ratio

from .preprocess import preprocess

EMBARQUE_RE = re.compile(r"\bEMB\d{6}\b", re.IGNORECASE)
PLATE_RE = re.compile(r"\b(?:[A-Z]{3}-?\d{4}|[A-Z]{3}-?\d[A-Z]\d{2})\b", re.IGNORECASE)
NF_RE = re.compile(r"\b\d{6,9}\b")
PLATE_SEPARATORS_RE = re.compile(r"[-\s]")
GENERIC_CARRIER_WORDS = {
    "a",
    "as",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "foi",
    "qual",
    "transportadora",
    "transportador",
    "carrier",
    "empresa",
    "frota",
    "dados",
    "buscar",
    "consulta",
    "consultar",
    "ou",
}


def normalize_plate(plate):
    return PLATE_SEPARATORS_RE.sub("", str(plate or "")).upper()


def extract_entities(text):
    return {
        "embarque": (EMBARQUE_RE.search(text) or [None])[0],
        "placa": (PLATE_RE.search(text) or [None])[0],
        "nf": (NF_RE.search(text) or [None])[0],
    }


def find_carriers(text, carriers, threshold=80):
    query = preprocess(text)
    query = EMBARQUE_RE.sub(" ", query)
    query = NF_RE.sub(" ", query)
    query = PLATE_RE.sub(" ", query)
    query_words = [word for word in query.split() if word not in GENERIC_CARRIER_WORDS]
    query = " ".join(query_words)
    if len(query.replace(" ", "")) < 2:
        return []
    query_numbers = set(re.findall(r"\b\d{1,2}\b", query))

    scored = sorted(
        (
            (
                carrier,
                _carrier_score(query, query_numbers, carrier),
            )
            for carrier in carriers
        ),
        key=lambda item: (-item[1], item[0]),
    )
    if not scored or scored[0][1] < threshold:
        return []
    best_score = scored[0][1]
    return [
        carrier
        for carrier, score in scored
        if score >= threshold and best_score - score <= 4
    ][:3]


def _carrier_score(query, query_numbers, carrier):
    normalized_name = preprocess(carrier)
    text_score = max(
        token_set_ratio(query, normalized_name),
        partial_ratio(query, normalized_name),
    )
    if not query_numbers:
        return text_score
    carrier_numbers = set(re.findall(r"\b\d{1,2}\b", normalized_name))
    if query_numbers & carrier_numbers:
        return max(text_score, 100)
    return text_score * 0.65
