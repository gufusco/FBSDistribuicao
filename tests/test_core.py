import asyncio
import sqlite3
from datetime import datetime, timedelta
from types import SimpleNamespace

from fbs_bot.nlp.classifier import build_pipeline, predict
from fbs_bot.nlp.entities import extract_entities, find_carriers
from fbs_bot.nlp.preprocess import preprocess
from fbs_bot.services.acesso import autorizado
from fbs_bot.services.auditoria import mascarar, purge
from fbs_bot.services.estadia import calcular_estadia
from fbs_bot.services.formatters import embarque, estadia


def test_preprocess():
    assert preprocess("Áção, NF!") == "acao nf"


def test_entities():
    entities = extract_entities("emb000123 AAA-1234 AAA1B23 nf 123456")
    assert entities["embarque"] == "emb000123"
    assert entities["placa"] == "AAA-1234"
    assert entities["nf"] == "123456"


def test_estadia_uses_exit_time_when_present():
    chegada = datetime(2026, 1, 1, 1)
    saida = datetime(2026, 1, 1, 8)
    result = calcular_estadia(
        chegada,
        agora=datetime(2030, 1, 1),
        saida=saida,
        valor_hora=60,
    )
    assert result["horas_totais"] == 7
    assert result["horas_excedentes"] == 2
    assert result["valor"] == 120


def test_estadia_clock_can_be_injected():
    now = datetime(2026, 1, 1, 10)
    assert calcular_estadia(now - timedelta(hours=5), now)["horas_excedentes"] == 0
    assert (
        calcular_estadia(now - timedelta(hours=7), now, valor_hora=60)["valor"] == 120
    )


def test_mask():
    assert "AAA1***" in mascarar("placa AAA1B23 nf 123456")
    assert "123456" not in mascarar("nf 123456")
    assert "R$ 385.26" not in mascarar("Valor estimado: R$ 385.26")


def test_access_profiles():
    assert autorizado({"perfil": "interno"})
    assert autorizado(
        {"perfil": "transportadora", "transportadora_id": 2},
        {"transportadora_id": 2},
    )
    assert not autorizado(
        {"perfil": "transportadora", "transportadora_id": 2},
        {"transportadora_id": 3},
    )
    assert autorizado(
        {"perfil": "motorista", "placa": "AAA1234"},
        {"placa": "AAA-1234"},
    )
    assert not autorizado(None)


def test_carrier_ambiguity_is_limited_to_top_matches():
    matches = find_carriers(
        "Transportadora 01 ou Transportadora 02",
        ["Transportadora 01", "Transportadora 02", "Transportadora 03"],
        threshold=80,
    )
    assert matches == ["Transportadora 01", "Transportadora 02"]


def test_audit_purge(tmp_path):
    connection = sqlite3.connect(tmp_path / "audit.db")
    connection.execute("CREATE TABLE auditoria(timestamp TEXT)")
    connection.execute("INSERT INTO auditoria VALUES ('2020-01-01')")
    connection.commit()
    purge(connection, 90, now=datetime(2026, 1, 1))
    assert connection.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0] == 0
    connection.close()


def test_classifier_smoke():
    texts = [
        "oi bom dia",
        "ola tudo bem",
        "bom dia assistente",
        "status do embarque",
        "consultar a carga",
        "onde esta a remessa",
        "previsao do tempo",
        "conte uma piada",
        "resultado do jogo",
    ]
    labels = ["saudacao"] * 3 + ["consultar_embarque"] * 3 + ["fora_escopo"] * 3
    model = build_pipeline("svc").fit(texts, labels)
    label, probability = predict(model, "status do embarque")
    assert label in model.classes_
    assert 0 <= probability <= 1


def test_engine_precedence_context_and_unknown(engine):
    assert "Olá" in engine.handle_message(1, "oi")
    assert "Informe" in engine.handle_message(1, "status do embarque")
    assert "Embarque EMB000001" in engine.handle_message(1, "EMB000001")
    assert "Não entendi" in engine.handle_message(1, "xyzzy sem contexto")
    assert "Informe" in engine.handle_message(1, "status do embarque")
    assert "não autorizado" in engine.handle_message(999, "oi").lower()

    engine.clock = lambda: 1_401
    assert "Informe" in engine.handle_message(1, "status do embarque")
    assert (
        engine.conn.execute(
            "SELECT COUNT(*) FROM auditoria WHERE chat_id=1"
        ).fetchone()[0]
        > 0
    )


def test_formatters_and_access_denial(engine):
    shipment = {
        "id": "EMB000010",
        "status": "em_transito",
        "placa": "ABC-0010",
        "doca": 1,
        "data": "2026-10-01T08:00:00",
    }
    assert "NF: 123456" in embarque(shipment, "Transportadora 01", ["123456"], [])
    assert "NF: Sem NF" in embarque(shipment, "Transportadora 01", [], [])
    patio = {
        "chegada_portaria": "2026-10-05T07:00:00",
        "saida": None,
    }
    assert "Horas excedentes" in estadia(
        patio, {"horas_totais": 7, "horas_excedentes": 2, "valor": 120}
    )
    assert "Sem estadia" in estadia(
        patio, {"horas_totais": 4, "horas_excedentes": 0, "valor": 0}
    )
    result = engine._query(
        "consultar_embarque",
        {"embarque": "EMB000001"},
        {"perfil": "transportadora", "transportadora_id": 999},
    )
    assert "Acesso negado" in result


def test_telegram_handlers_use_effective_message_and_distinct_help():
    from fbs_bot.channels import telegram_bot

    class FakeMessage:
        def __init__(self, text=None):
            self.text = text
            self.replies = []

        async def reply_text(self, text):
            self.replies.append(text)

    async def exercise_handlers():
        start_message = FakeMessage()
        help_message = FakeMessage()
        await telegram_bot.start(SimpleNamespace(effective_message=start_message), None)
        await telegram_bot.help_command(
            SimpleNamespace(effective_message=help_message), None
        )
        return start_message.replies[0], help_message.replies[0]

    start_reply, help_reply = asyncio.run(exercise_handlers())
    assert "Olá!" in start_reply
    assert "consulta" in help_reply
    assert start_reply != help_reply
    assert not hasattr(telegram_bot, "engine")
