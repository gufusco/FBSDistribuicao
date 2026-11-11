from datetime import datetime

def calcular_estadia(chegada, agora=None, tolerancia_horas=5, valor_hora=None):
    if isinstance(chegada, str):
        chegada = datetime.fromisoformat(chegada)
    agora = agora or datetime.now()
    horas = max(0.0, (agora - chegada).total_seconds() / 3600 - tolerancia_horas)
    result = {"horas_excedentes": round(horas, 2)}
    if valor_hora is not None:
        result["valor"] = round(horas * valor_hora, 2)
    return result
