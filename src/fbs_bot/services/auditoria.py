import re
from datetime import datetime, timedelta

def mascarar(text):
    text = re.sub(r"\b([A-Z]{3})([- ]?\d)(\w{2,4})\b", r"\1\2***", text, flags=re.I)
    return re.sub(r"\b(\d{3})\d{3,6}\b", r"\1***", text)

def purge(conn, days=90):
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    conn.execute("DELETE FROM auditoria WHERE timestamp < ?", (cutoff,))
    conn.commit()
