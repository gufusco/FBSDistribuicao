import re

def keyword_intent(text):
    t = text.lower()
    if re.search(r"\b(oi|ola|bom dia|boa tarde|obrigad|tchau|ate logo|valeu)\b", t):
        return "saudacao"
    if re.search(r"\b(ajuda|comandos|o que voce faz)\b", t):
        return "ajuda"
    if re.search(r"\b(ocorrencia|ocorrencias|avaria|atraso)\b", t):
        return "consultar_ocorrencia"
    if re.search(r"\b(agendamento|agenda|doca)\b", t):
        return "consultar_agendamento"
    if re.search(r"\b(estadia|horas no patio|permanencia)\b", t):
        return "consultar_estadia"
    if re.search(r"\b(transportadora|carrier|frota)\b", t):
        return "consultar_transportadora"
    if re.search(r"\b(nota fiscal|danfe|\bnf\b)\b", t):
        return "consultar_nota_fiscal"
    if re.search(r"\b(placa|veiculo|caminhao|carreta)\b", t):
        return "consultar_veiculo_patio"
    if re.search(r"\b(embarque|carga|remessa|envio)\b", t):
        return "consultar_embarque"
    return None
