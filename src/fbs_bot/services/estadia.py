from datetime import datetime


def calcular_estadia(
    chegada,
    agora=None,
    tolerancia_horas=5,
    valor_hora=None,
    saida=None,
):
    chegada = datetime.fromisoformat(chegada) if isinstance(chegada, str) else chegada
    saida = datetime.fromisoformat(saida) if isinstance(saida, str) else saida
    fim = saida or agora or datetime.now()
    horas_totais = max(0.0, (fim - chegada).total_seconds() / 3600)
    horas = max(0.0, horas_totais - tolerancia_horas)
    result = {
        "horas_totais": round(horas_totais, 2),
        "horas_excedentes": round(horas, 2),
        "encerrada": saida is not None,
    }
    if valor_hora is not None:
        result["valor"] = round(horas * valor_hora, 2)
    return result
