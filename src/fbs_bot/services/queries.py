def get_user(conn, chat_id):
    row = conn.execute("SELECT * FROM usuarios WHERE chat_id=?", (chat_id,)).fetchone()
    return dict(row) if row else None

def get_by_embarque(conn, code):
    row = conn.execute("SELECT * FROM tms.embarques WHERE id=?", (code.upper(),)).fetchone()
    return dict(row) if row else None

def get_by_nf(conn, nf):
    return conn.execute("SELECT * FROM tms.notas_fiscais WHERE numero=?", (str(nf),)).fetchone()

def get_by_plate(conn, plate):
    return conn.execute("SELECT * FROM patio.movimentacao WHERE placa=?", (plate.upper(),)).fetchone()

def get_patio_by_embarque(conn, code):
    return conn.execute("SELECT * FROM patio.movimentacao WHERE embarque=?", (code.upper(),)).fetchone()

def carriers(conn):
    return [r["nome"] for r in conn.execute("SELECT nome FROM tms.transportadoras").fetchall()]

def carrier_id(conn, name):
    row = conn.execute("SELECT id FROM tms.transportadoras WHERE nome=?", (name,)).fetchone()
    return row["id"] if row else None

def nfs_for_embarque(conn, code):
    return [r["numero"] for r in conn.execute("SELECT numero FROM tms.notas_fiscais WHERE embarque_id=?", (code,))]

def occurrences_for_embarque(conn, code):
    return [dict(r) for r in conn.execute("SELECT tipo,descricao FROM ocorr.ocorrencias WHERE embarque=?", (code,))]

def agendamento_for_embarque(conn, code):
    return conn.execute("SELECT * FROM tms.agendamentos WHERE embarque_id=?", (code,)).fetchone()

def embarques_for_carrier(conn, cid):
    return [dict(r) for r in conn.execute("SELECT * FROM tms.embarques WHERE transportadora_id=?", (cid,))]
