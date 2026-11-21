import sqlite3
import time
from datetime import datetime
from pathlib import Path

from .config import (
    AUDIT_RETENTION_DAYS,
    DATA_DIR,
    FALLBACK_THRESHOLD,
    MODEL_PATH,
    VALOR_HORA_ESTADIA,
)
from .nlp.classifier import load_model, predict
from .nlp.entities import extract_entities, find_carriers, normalize_plate
from .nlp.rules import keyword_intent
from .services.acesso import autorizado
from .services.auditoria import mascarar, purge
from .services.estadia import calcular_estadia
from .services.formatters import (
    agendamento as fmt_agendamento,
)
from .services.formatters import (
    embarque as fmt_embarque,
)
from .services.formatters import (
    estadia as fmt_estadia,
)
from .services.formatters import (
    nota_fiscal as fmt_nf,
)
from .services.formatters import (
    ocorrencia as fmt_ocorrencia,
)
from .services.formatters import (
    transportadora as fmt_transportadora,
)
from .services.formatters import (
    veiculo as fmt_veiculo,
)
from .services.queries import (
    agendamento_for_embarque,
    carrier_id,
    carriers,
    embarques_for_carrier,
    get_by_embarque,
    get_by_nf,
    get_by_plate,
    get_patio_by_embarque,
    get_user,
    nfs_for_embarque,
    occurrences_for_embarque,
)

INTENT_LABELS = {
    "consultar_embarque": "embarque",
    "consultar_agendamento": "agendamento",
    "consultar_nota_fiscal": "nota fiscal",
    "consultar_veiculo_patio": "veículo no pátio",
    "consultar_ocorrencia": "ocorrência",
    "consultar_estadia": "estadia",
    "consultar_transportadora": "transportadora",
}
FOLLOWUP_KEYS = {
    "consultar_embarque": ("embarque",),
    "consultar_agendamento": ("embarque", "placa"),
    "consultar_ocorrencia": ("embarque",),
    "consultar_nota_fiscal": ("nf",),
    "consultar_veiculo_patio": ("placa",),
    "consultar_estadia": ("embarque", "placa"),
}
NOT_FOUND = "Não encontrei esse registro. Confira o identificador e tente novamente."
UNAUTHORIZED = "Acesso não autorizado."
DENIED = "🔒 Acesso negado para este registro."
HELP_REPLY = (
    "Posso consultar embarques, agendamentos, notas fiscais, pátio, "
    "ocorrências, estadia e transportadoras."
)


class Engine:
    def __init__(
        self,
        data_dir=DATA_DIR,
        model_path=MODEL_PATH,
        clock=None,
        wall_clock=None,
        retention_days=AUDIT_RETENTION_DAYS,
    ):
        self.data_dir = Path(data_dir)
        self.clock = clock or time.monotonic
        self.wall_clock = wall_clock or datetime.now
        self.retention_days = retention_days
        self.context = {}

        required_databases = (
            "app.db",
            "tms.db",
            "patio.db",
            "ocorrencias.db",
        )
        missing = [
            str(self.data_dir / name)
            for name in required_databases
            if not (self.data_dir / name).is_file()
        ]
        if missing:
            raise FileNotFoundError(
                "Bancos do assistente ausentes: "
                + ", ".join(missing)
                + ". Gere-os com python scripts/seed_db.py."
            )

        if model_path is None:
            self.model = None
        else:
            model_path = Path(model_path)
            if not model_path.is_file():
                raise FileNotFoundError(
                    f"Modelo ausente: {model_path}. "
                    "Treine-o com python scripts/train.py."
                )
            self.model = load_model(model_path)

        self.conn = sqlite3.connect(self.data_dir / "app.db")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("ATTACH DATABASE ? AS tms", (str(self.data_dir / "tms.db"),))
        self.conn.execute(
            "ATTACH DATABASE ? AS patio", (str(self.data_dir / "patio.db"),)
        )
        self.conn.execute(
            "ATTACH DATABASE ? AS ocorr",
            (str(self.data_dir / "ocorrencias.db"),),
        )
        self.conn.execute("SELECT 1 FROM auditoria LIMIT 0")
        purge(self.conn, self.retention_days, self.wall_clock())
        self.last_purge = self.clock()

    def handle_message(self, chat_id, text):
        now = self.clock()
        user = get_user(self.conn, chat_id)
        if not user:
            self._audit(chat_id, text, "nao_autorizado", 0.0, {}, UNAUTHORIZED)
            return UNAUTHORIZED

        self._purge_if_due(now)
        context = self.context.get(chat_id)
        if context and now - context["time"] > 300:
            self.context.pop(chat_id, None)
            context = None

        if context and context.get("choices"):
            result = self._handle_carrier_choice(chat_id, text, user, context)
            if result is not None:
                return result

        entities = extract_entities(text)
        entities["_text"] = text
        intent = keyword_intent(text)

        if (
            context
            and context.get("intent")
            and not intent
            and self._required_key(context["intent"], entities)
        ):
            intent = context["intent"]
        self.context.pop(chat_id, None)

        names = carriers(self.conn)
        exact = [name for name in names if name.casefold() in text.casefold()]
        matches = exact or find_carriers(text, names)
        entities["_carriers"] = matches

        if not intent:
            if matches:
                intent = "consultar_transportadora"
            elif entities["embarque"]:
                intent = "consultar_embarque"
            elif self._is_isolated_plate(text, entities.get("placa")):
                intent = "consultar_veiculo_patio"
            elif entities["nf"] and text.strip() == entities["nf"]:
                intent = "consultar_nota_fiscal"
        if not intent and self.model is not None:
            intent, probability = predict(self.model, text)
        else:
            probability = 1.0
        if not intent or probability < FALLBACK_THRESHOLD:
            intent = "fora_escopo"

        if intent == "saudacao":
            result = "Olá! " + HELP_REPLY
        elif intent == "ajuda":
            result = HELP_REPLY
        elif intent == "fora_escopo":
            result = "Não entendi. " + HELP_REPLY
        elif intent == "consultar_transportadora" and len(matches) > 1:
            self.context[chat_id] = {
                "choices": matches,
                "time": now,
                "text": text,
            }
            result = "Encontrei mais de uma transportadora. Escolha:\n" + "\n".join(
                f"{index}. {name}" for index, name in enumerate(matches, start=1)
            )
        else:
            if intent == "consultar_transportadora":
                has_key = bool(matches or entities.get("embarque"))
            else:
                has_key = self._required_key(intent, entities) is not None
            if not has_key:
                self.context[chat_id] = {"intent": intent, "time": now}
                result = (
                    "Informe o identificador para consultar "
                    f"{INTENT_LABELS.get(intent, 'essa informação')}."
                )
            else:
                result = self._query(intent, entities, user)

        self._audit(chat_id, text, intent, probability, entities, result, user)
        return result

    @staticmethod
    def _is_isolated_plate(text, plate):
        return bool(plate and normalize_plate(text.strip()) == normalize_plate(plate))

    @staticmethod
    def _required_key(intent, entities):
        for key in FOLLOWUP_KEYS.get(intent, ()):
            if entities.get(key):
                return entities[key]
        return None

    def _handle_carrier_choice(self, chat_id, text, user, context):
        try:
            choice = int(text.strip()) - 1
        except ValueError:
            return None
        if not 0 <= choice < len(context["choices"]):
            return None

        self.context.pop(chat_id, None)
        name = context["choices"][choice]
        entities = {
            "_text": context.get("text", ""),
            "_carriers": [name],
            "embarque": None,
            "placa": None,
            "nf": None,
        }
        result = self._query("consultar_transportadora", entities, user)
        self._audit(
            chat_id,
            text,
            "consultar_transportadora",
            1.0,
            entities,
            result,
            user,
        )
        return result

    def _shipment(self, code, user):
        shipment = get_by_embarque(self.conn, code) if code else None
        if shipment and not autorizado(user, shipment, shipment.get("placa")):
            return shipment, DENIED
        return shipment, None

    def _query(self, intent, entities, user):
        code = entities.get("embarque")
        plate = entities.get("placa")

        if intent == "consultar_embarque":
            shipment, denied = self._shipment(code, user)
            if denied:
                return denied
            if not shipment:
                return NOT_FOUND
            carrier = self.conn.execute(
                "SELECT nome FROM tms.transportadoras WHERE id=?",
                (shipment["transportadora_id"],),
            ).fetchone()
            return fmt_embarque(
                shipment,
                carrier["nome"] if carrier else None,
                nfs_for_embarque(self.conn, shipment["id"]),
                occurrences_for_embarque(self.conn, shipment["id"]),
            )

        if intent == "consultar_agendamento":
            if not code and plate:
                patio_record = get_by_plate(self.conn, plate)
                code = patio_record["embarque"] if patio_record else None
            shipment, denied = self._shipment(code, user)
            if denied:
                return denied
            if not shipment:
                return NOT_FOUND
            appointment = agendamento_for_embarque(self.conn, code)
            return fmt_agendamento(dict(appointment)) if appointment else NOT_FOUND

        if intent == "consultar_ocorrencia":
            shipment, denied = self._shipment(code, user)
            if denied:
                return denied
            if not shipment:
                return NOT_FOUND
            return fmt_ocorrencia(occurrences_for_embarque(self.conn, code), code)

        if intent == "consultar_nota_fiscal":
            invoice = get_by_nf(self.conn, entities.get("nf"))
            if not invoice:
                return NOT_FOUND
            shipment, denied = self._shipment(invoice["embarque_id"], user)
            if denied:
                return denied
            return fmt_nf(dict(invoice))

        if intent == "consultar_veiculo_patio":
            movement = get_by_plate(self.conn, plate)
            if not movement:
                return NOT_FOUND
            shipment, denied = self._shipment(movement["embarque"], user)
            if denied:
                return denied
            if not autorizado(user, shipment, movement["placa"]):
                return DENIED
            return fmt_veiculo(dict(movement))

        if intent == "consultar_estadia":
            movement = (
                get_patio_by_embarque(self.conn, code)
                if code
                else get_by_plate(self.conn, plate)
            )
            if not movement:
                return NOT_FOUND
            shipment, denied = self._shipment(movement["embarque"], user)
            if denied:
                return denied
            if not autorizado(user, shipment, movement["placa"]):
                return DENIED
            if not movement["chegada_portaria"]:
                return "Não há horário de chegada registrado para calcular a estadia."
            calculation = calcular_estadia(
                movement["chegada_portaria"],
                agora=self.wall_clock(),
                saida=movement["saida"],
                valor_hora=VALOR_HORA_ESTADIA,
            )
            return fmt_estadia(dict(movement), calculation)

        if intent == "consultar_transportadora":
            name = (entities.get("_carriers") or [None])[0]
            if code:
                shipment, denied = self._shipment(code, user)
                if denied:
                    return denied
                if not shipment:
                    return NOT_FOUND
                carrier = self.conn.execute(
                    "SELECT id, nome FROM tms.transportadoras WHERE id=?",
                    (shipment["transportadora_id"],),
                ).fetchone()
                if not carrier:
                    return NOT_FOUND
                name = carrier["nome"]
                if user["perfil"] == "motorista":
                    return fmt_transportadora(name, [shipment])
            if not name:
                return NOT_FOUND
            identifier = carrier_id(self.conn, name)
            if identifier is None:
                return NOT_FOUND
            if user["perfil"] == "transportadora":
                if user.get("transportadora_id") != identifier:
                    return DENIED
            elif user["perfil"] != "interno":
                return DENIED
            return fmt_transportadora(
                name, embarques_for_carrier(self.conn, identifier)
            )

        return NOT_FOUND

    def _purge_if_due(self, now):
        if now - self.last_purge >= 86400:
            purge(self.conn, self.retention_days, self.wall_clock())
            self.last_purge = now

    def _audit(self, chat_id, text, intent, probability, entities, result, user=None):
        user = user or get_user(self.conn, chat_id)
        self.conn.execute(
            "INSERT INTO auditoria VALUES (?,?,?,?,?,?,?)",
            (
                self.wall_clock().isoformat(),
                chat_id,
                user["perfil"] if user else None,
                mascarar(text),
                intent,
                probability,
                mascarar(result),
            ),
        )
        self.conn.commit()
