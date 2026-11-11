from datetime import datetime

def dt(value):
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(str(value)).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(value)

def embarque(row, carrier, nfs, occurrences):
    occurrence_names = [o.get("tipo", str(o)) if isinstance(o, dict) else str(o) for o in occurrences]
    lines = [f"📦 Embarque {row['id']}", f"Status: {str(row['status']).replace('_',' ').title()}",
             f"Transportadora: {carrier or '—'}", f"Placa: {row.get('placa') or '—'}",
             f"Doca: {row.get('doca') or '—'}", f"Data: {dt(row.get('data'))}",
             f"NF: {', '.join(nfs) if nfs else 'Sem NF'}",
             f"Ocorrências: {', '.join(occurrence_names) if occurrence_names else 'Nenhuma'}"]
    return "\n".join(lines)

def agendamento(row):
    return "\n".join(["📅 Agendamento", f"Embarque: {row.get('embarque_id', row.get('embarque','—'))}",
                      f"Data: {dt(row.get('data'))}", f"Doca: {row.get('doca','—')}",
                      f"Status: {row.get('status','Agendado')}"])

def nota_fiscal(row):
    return "\n".join(["🧾 Nota fiscal", f"Número: {row['numero']}",
                      f"Embarque: {row.get('embarque_id','—')}", f"Status: {row.get('status','Emitida')}"])

def veiculo(row):
    return "\n".join(["🚚 Veículo no pátio", f"Placa: {row['placa']}",
                      f"Embarque: {row.get('embarque','—')}", f"Chegada: {dt(row.get('chegada_portaria'))}",
                      f"Entrada doca: {dt(row.get('entrada_doca'))}", f"Saída: {dt(row.get('saida'))}"])

def ocorrencia(rows, code):
    body = [f"⚠️ Ocorrências {code}"]
    body.extend(f"- {r['tipo'].title()}: {r['descricao']}" for r in rows)
    return "\n".join(body) if rows else f"✅ Ocorrências {code}\nNenhuma ocorrência registrada."

def estadia(row, calc):
    if not row:
        return "🕒 Estadia\nNenhum registro de pátio encontrado."
    if calc["horas_excedentes"] <= 0:
        return f"🕒 Estadia\nTempo no pátio: chegada {dt(row['chegada_portaria'])}\nTolerância: 5h\nSem estadia excedente."
    return "\n".join(["🕒 Estadia", f"Tempo no pátio: chegada {dt(row['chegada_portaria'])}",
                      "Tolerância: 5h", f"Horas excedentes: {calc['horas_excedentes']:.2f}h",
                      f"Valor: R$ {calc['valor']:.2f}"])

def transportadora(name, rows):
    return "\n".join([f"🏢 Transportadora {name}", f"Embarques: {len(rows)}",
                      *[f"- {r['id']}: {r['status'].replace('_',' ')}" for r in rows[:5]],
                      *([] if len(rows) <= 5 else [f"... e mais {len(rows)-5}"])])
