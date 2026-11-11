import sqlite3, time
from datetime import datetime
from .config import DATA_DIR, MODEL_PATH, FALLBACK_THRESHOLD, VALOR_HORA_ESTADIA
from .nlp.entities import extract_entities, find_carriers
from .nlp.rules import keyword_intent
from .nlp.classifier import load_model, predict
from .services.queries import (get_user, get_by_embarque, get_by_nf, get_by_plate, get_patio_by_embarque,
    carriers, carrier_id, nfs_for_embarque, occurrences_for_embarque, agendamento_for_embarque, embarques_for_carrier)
from .services.estadia import calcular_estadia
from .services.acesso import autorizado
from .services.auditoria import mascarar
from .services.formatters import embarque as fmt_embarque, agendamento as fmt_agendamento, nota_fiscal as fmt_nf
from .services.formatters import veiculo as fmt_veiculo, ocorrencia as fmt_ocorrencia, estadia as fmt_estadia, transportadora as fmt_transportadora

INTENT_LABELS = {"consultar_embarque":"embarque", "consultar_agendamento":"agendamento",
"consultar_nota_fiscal":"nota fiscal", "consultar_veiculo_patio":"veiculo no patio",
"consultar_ocorrencia":"ocorrencia", "consultar_estadia":"estadia",
"consultar_transportadora":"transportadora", "ajuda":"ajuda", "saudacao":"saudacao"}

class Engine:
    def __init__(self, data_dir=DATA_DIR, model_path=MODEL_PATH, clock=None):
        self.data_dir, self.clock = data_dir, clock or time.time
        self.model = load_model(model_path) if model_path.exists() else None
        self.context = {}
        self.conn = sqlite3.connect(data_dir / "app.db")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("ATTACH DATABASE ? AS tms", (str(data_dir / "tms.db"),))
        self.conn.execute("ATTACH DATABASE ? AS patio", (str(data_dir / "patio.db"),))
        self.conn.execute("ATTACH DATABASE ? AS ocorr", (str(data_dir / "ocorrencias.db"),))

    def handle_message(self, chat_id, text):
        now = self.clock()
        if chat_id in self.context and self.context[chat_id].get("choices"):
            try:
                choice = int(text.strip()) - 1
                options = self.context[chat_id]["choices"]
                if 0 <= choice < len(options):
                    self.context.pop(chat_id, None)
                    return f"Transportadora escolhida: {options[choice]}"
            except ValueError:
                pass
        ctx = self.context.get(chat_id)
        entities = extract_entities(text)
        pending = ctx.get("intent") if ctx and now - ctx["time"] <= 300 else None
        self.context.pop(chat_id, None)
        if pending and not keyword_intent(text) and self._required_key(pending, entities):
            intent = pending
        else:
            intent = keyword_intent(text)
        entities["_text"] = text
        carrier_names = carriers(self.conn)
        exact_carriers = [c for c in carrier_names if c.lower() in text.lower()]
        similar = exact_carriers or find_carriers(text, carrier_names)
        entities["_carriers"] = similar
        if len(similar) > 1 and not entities["embarque"]:
            self.context[chat_id] = {"choices": similar, "time": now}
            reply = "Encontrei mais de uma transportadora. Escolha:\n" + "\n".join(f"{i+1}. {v}" for i,v in enumerate(similar))
            self._audit(chat_id, text, "consultar_transportadora", 1.0, entities, reply)
            return reply
        probability = 1.0
        if not intent and text.strip().upper().startswith("EMB") and entities["embarque"]:
            intent = "consultar_embarque"
        elif not intent and entities["placa"] and text.strip().upper().replace("-","") == entities["placa"].replace("-","").upper():
            intent = "consultar_veiculo_patio"
        elif not intent and entities["nf"] and text.strip() == entities["nf"]:
            intent = "consultar_nota_fiscal"
        elif not intent and self.model:
            intent, probability = predict(self.model, text)
        if not intent or probability < FALLBACK_THRESHOLD:
            intent = "fora_escopo"
        user = get_user(self.conn, chat_id)
        if not user:
            self._audit(chat_id, text, intent, probability, entities, "nao autorizado")
            return "Acesso nao autorizado."
        if intent in ("saudacao","ajuda"):
            reply = "Ola! Posso consultar embarques, agendamentos, NFs, patio, ocorrencias, estadia e transportadoras." if intent=="saudacao" else "Envie um EMBxxxxxx, placa ou NF, ou pergunte sobre embarque, patio, estadia e ocorrencias."
        elif intent == "fora_escopo":
            reply = "Nao entendi. Posso consultar embarques, agendamentos, NFs, patio, ocorrencias, estadia e transportadoras."
        else:
            key = self._required_key(intent, entities)
            if intent == "consultar_transportadora":
                key = True if similar else None
            if not key:
                self.context[chat_id] = {"intent": intent, "time": now}
                reply = f"Informe o identificador para consultar {INTENT_LABELS.get(intent, intent)}."
            else:
                reply = self._query(intent, entities, user)
        self._audit(chat_id, text, intent, probability, entities, reply)
        return reply

    @staticmethod
    def _required_key(intent, e):
        needs = {
            "consultar_embarque": ("embarque",),
            "consultar_agendamento": ("embarque", "placa"),
            "consultar_ocorrencia": ("embarque",),
            "consultar_nota_fiscal": ("nf",),
            "consultar_veiculo_patio": ("placa",),
            "consultar_estadia": ("embarque", "placa"),
        }
        for name in needs.get(intent, ()):
            if e.get(name):
                return e[name]
        return None

    def _query(self, intent, e, user):
        row = None
        if intent == "consultar_embarque":
            row = get_by_embarque(self.conn, e["embarque"])
            if row and not autorizado(user, row):
                return "🔒 Acesso negado para este embarque."
            if row:
                return fmt_embarque(row, self.conn.execute("SELECT nome FROM tms.transportadoras WHERE id=?", (row["transportadora_id"],)).fetchone()["nome"], nfs_for_embarque(self.conn,row["id"]), occurrences_for_embarque(self.conn,row["id"]))
        elif intent == "consultar_agendamento":
            code=e.get("embarque")
            if not code and e.get("placa"):
                patio_row=get_by_plate(self.conn,e["placa"])
                code=patio_row["embarque"] if patio_row else None
            row=agendamento_for_embarque(self.conn, code) if code else None
            if row: return fmt_agendamento(dict(row))
        elif intent == "consultar_ocorrencia":
            code=e.get("embarque")
            return fmt_ocorrencia(occurrences_for_embarque(self.conn,code), code) if code else "⚠️ Informe o EMB do embarque."
        elif intent == "consultar_nota_fiscal":
            row = get_by_nf(self.conn, e["nf"])
            if row: return fmt_nf(dict(row))
        elif intent == "consultar_veiculo_patio":
            row = get_by_plate(self.conn, e["placa"].upper())
            if row: return fmt_veiculo(dict(row))
        elif intent == "consultar_estadia":
            row = get_patio_by_embarque(self.conn, e["embarque"]) if e.get("embarque") else get_by_plate(self.conn, e["placa"].upper())
            if row and row["chegada_portaria"]:
                calc = calcular_estadia(row["chegada_portaria"], valor_hora=VALOR_HORA_ESTADIA)
                return fmt_estadia(dict(row), calc)
        elif intent == "consultar_transportadora":
            name = (e.get("_carriers") or find_carriers(e.get("_text",""), carriers(self.conn)) or [None])[0]
            if name:
                cid=carrier_id(self.conn,name)
                rows=embarques_for_carrier(self.conn,cid)
                if user["perfil"] == "transportadora" and user.get("transportadora_id") != cid:
                    return "🔒 Acesso negado para esta transportadora."
                return fmt_transportadora(name,rows)
        else:
            row = None
        if row is None: return "Não encontrei esse registro. Confira o identificador e tente novamente."
        if not autorizado(user, dict(row) if intent=="consultar_embarque" else None, e.get("placa")):
            return "🔒 Acesso negado para este registro."
        return "Consulta concluída."

    def _audit(self, chat_id, text, intent, probability, entities, result):
        user = get_user(self.conn, chat_id)
        self.conn.execute("INSERT INTO auditoria VALUES (?,?,?,?,?,?,?)", (datetime.now().isoformat(), chat_id, user["perfil"] if user else None, mascarar(text), intent, probability, result))
        self.conn.commit()
