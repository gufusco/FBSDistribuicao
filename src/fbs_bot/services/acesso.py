def autorizado(usuario, embarque=None, placa=None):
    if not usuario:
        return False
    if usuario["perfil"] == "interno":
        return True
    if usuario["perfil"] == "motorista":
        return bool(placa and usuario.get("placa") == placa)
    if usuario["perfil"] == "transportadora":
        return bool(embarque and usuario.get("transportadora_id") == embarque.get("transportadora_id"))
    return False
