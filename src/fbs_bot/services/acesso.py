from fbs_bot.nlp.entities import normalize_plate


def autorizado(usuario, embarque=None, placa=None):
    if not usuario:
        return False
    if usuario["perfil"] == "interno":
        return True
    if usuario["perfil"] == "motorista":
        target_plate = placa or (embarque or {}).get("placa")
        return bool(
            target_plate
            and normalize_plate(usuario.get("placa")) == normalize_plate(target_plate)
        )
    if usuario["perfil"] == "transportadora":
        return bool(
            embarque
            and usuario.get("transportadora_id") == embarque.get("transportadora_id")
        )
    return False
