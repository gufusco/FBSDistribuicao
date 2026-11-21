import re
from datetime import datetime, timedelta


def mascarar(text):
    text = re.sub(
        r"\b([A-Z]{3})([- ]?\d)(\w{2,4})\b", r"\1\2***", text, flags=re.IGNORECASE
    )
    text = re.sub(r"\b(\d{3})\d{3,6}\b", r"\1***", text)
    return re.sub(r"(?i)\bR\$\s*[\d.]+(?:,\d{2})?\b", "R$ ***", text)


def purge(conn, days=90, now=None):
    cutoff = ((now or datetime.now()) - timedelta(days=days)).isoformat()
    conn.execute("DELETE FROM auditoria WHERE timestamp < ?", (cutoff,))
    conn.commit()
