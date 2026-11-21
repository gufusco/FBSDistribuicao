import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from generate_corpus import generate_dev_corpus, generate_ood_corpus
from seed_db import seed_database

from fbs_bot.nlp.entities import extract_entities, find_carriers
from fbs_bot.nlp.rules import keyword_intent
from fbs_bot.services.queries import get_by_plate


def test_authorization_applies_to_every_intent(engine):
    restricted_queries = (
        "nf 123456",
        "agendamento do EMB000002",
        "ocorrencias do EMB000002",
        "estadia do EMB000002",
        "placa ABC0005",
        "transportadora Transportadora 02",
    )
    for query in restricted_queries:
        assert "Acesso negado" in engine.handle_message(2, query), query

    assert "Acesso negado" in engine.handle_message(3, "placa ABC0005")
    assert "Embarque EMB000001" in engine.handle_message(3, "EMB000001")
    assert "Número: 654321" in engine.handle_message(3, "nf 654321")
    assert "Agendamento" in engine.handle_message(3, "agendamento do EMB000001")
    assert "atraso" in engine.handle_message(3, "ocorrencias do EMB000001").lower()
    assert "Estadia" in engine.handle_message(3, "estadia do EMB000001")

    assert "Acesso negado" in engine.handle_message(
        3, "transportadora Transportadora 01"
    )
    assert "Embarque EMB000001" in engine.handle_message(2, "EMB000001")
    assert "Número: 654321" in engine.handle_message(2, "nf 654321")
    assert "Agendamento" in engine.handle_message(2, "agendamento do EMB000001")
    assert "atraso" in engine.handle_message(2, "ocorrencias do EMB000001").lower()
    assert "Placa: AAA-1234" in engine.handle_message(2, "placa AAA1234")
    assert "Estadia" in engine.handle_message(2, "estadia do EMB000001")


def test_unknown_user_is_rejected_before_carrier_lookup(engine):
    assert "Acesso nao autorizado" in engine.handle_message(
        999, "transportadora Transportadora 02"
    ).replace("não", "nao")


def test_accented_keywords_are_normalized():
    assert keyword_intent("Olá") == "saudacao"
    assert keyword_intent("ocorrências") == "consultar_ocorrencia"
    assert keyword_intent("veículo no pátio") == "consultar_veiculo_patio"
    assert keyword_intent("permanência") == "consultar_estadia"
    assert keyword_intent("até logo") == "saudacao"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Bom dia, status do EMB000001", "consultar_embarque"),
        ("Oi, ocorrências do EMB000001", "consultar_ocorrencia"),
    ],
)
def test_operational_intent_wins_over_greeting(engine, text, expected):
    result = engine.handle_message(1, text)
    if expected == "consultar_embarque":
        assert "Embarque EMB000001" in result
    else:
        assert "atraso" in result.lower()


def test_carrier_typo_returns_only_relevant_matches():
    candidates = [f"Transportadora {index:02d}" for index in range(1, 31)]
    matches = find_carriers("transportadra 05", candidates)
    assert matches
    assert matches[0] == "Transportadora 05"
    assert len(matches) <= 3


def test_carrier_choice_runs_authorized_query_and_audits(engine):
    prompt = engine.handle_message(1, "Transportadora 01 ou Transportadora 02")
    assert "Escolha" in prompt
    result = engine.handle_message(1, "1")
    assert "Transportadora 01" in result
    assert "Embarques:" in result
    assert (
        engine.conn.execute(
            "SELECT COUNT(*) FROM auditoria WHERE chat_id=1"
        ).fetchone()[0]
        == 2
    )


def test_carrier_typo_resolves_to_specific_company(engine):
    result = engine.handle_message(1, "transportadra 05")
    assert "Transportadora 05" in result
    assert "Embarques:" in result
    assert "Transportadora 01" not in result


def test_carrier_choice_obeys_access_control(engine):
    prompt = engine.handle_message(3, "Transportadora 01 ou Transportadora 02")
    assert "Escolha" in prompt
    result = engine.handle_message(3, "1")
    assert "Acesso negado" in result
    assert (
        engine.conn.execute(
            "SELECT COUNT(*) FROM auditoria WHERE chat_id=3"
        ).fetchone()[0]
        == 2
    )


def test_expired_carrier_choice_is_not_used(engine):
    engine.handle_message(1, "Transportadora 01 ou Transportadora 02")
    engine.clock = lambda: 1_301
    result = engine.handle_message(1, "1")
    assert "Transportadora escolhida" not in result
    assert "Não entendi" in result


def test_carrier_query_can_use_embarque_instead_of_missing_carrier_name(engine):
    result = engine.handle_message(1, "qual foi a transportadora do EMB000001")
    assert "Transportadora 01" in result
    driver_result = engine.handle_message(3, "qual foi a transportadora do EMB000001")
    assert "Transportadora 01" in driver_result
    assert "Embarques: 1" in driver_result


def test_plate_lookup_normalizes_hyphen_and_case(engine):
    assert get_by_plate(engine.conn, "aaa1234")["embarque"] == "EMB000001"
    assert get_by_plate(engine.conn, "AAA-1234")["embarque"] == "EMB000001"


def test_audit_masks_sensitive_values_in_both_input_and_result(engine):
    engine.handle_message(1, "placa AAA-1234")
    text, result = engine.conn.execute(
        "SELECT masked_text, result FROM auditoria ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    assert "AAA-1234" not in text
    assert "AAA-1234" not in result


def test_nonexistent_embarque_has_no_occurrence_is_not_reported(engine):
    result = engine.handle_message(1, "ocorrencias do EMB999999")
    assert "não encontrei" in result.lower()


def test_plate_regex_does_not_accept_space_separated_words():
    assert extract_entities("emb 1234")["placa"] is None
    assert extract_entities("ola 1234")["placa"] is None


def test_missing_database_and_model_fail_at_startup(engine, tmp_path):
    from fbs_bot.engine import Engine

    with pytest.raises(FileNotFoundError, match="Bancos do assistente ausentes"):
        Engine(data_dir=tmp_path / "empty", model_path=None)
    with pytest.raises(FileNotFoundError, match="Modelo ausente"):
        Engine(
            data_dir=engine.data_dir,
            model_path=engine.data_dir / "missing-model.joblib",
        )


def test_audit_retention_is_run_periodically(engine):
    engine.conn.execute(
        "INSERT INTO auditoria VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("2000-01-01T00:00:00", 1, "interno", "old", "saudacao", 1.0, "old"),
    )
    engine.conn.commit()
    engine.last_purge = 0
    engine.clock = lambda: 90_000
    engine.handle_message(1, "oi")
    count = engine.conn.execute(
        "SELECT COUNT(*) FROM auditoria WHERE intent='saudacao' "
        "AND timestamp<'2020-01-01'"
    ).fetchone()[0]
    assert count == 0


def test_seed_script_can_create_isolated_synthetic_databases(tmp_path):
    seed_database(tmp_path)
    assert {path.name for path in tmp_path.glob("*.db")} == {
        "app.db",
        "tms.db",
        "patio.db",
        "ocorrencias.db",
    }
    connection = sqlite3.connect(tmp_path / "tms.db")
    assert connection.execute("SELECT COUNT(*) FROM embarques").fetchone()[0] == 500
    assert (
        connection.execute("SELECT COUNT(*) FROM notas_fiscais").fetchone()[0] == 1500
    )
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM embarques e "
            "WHERE NOT EXISTS (SELECT 1 FROM notas_fiscais n "
            "WHERE n.embarque_id=e.id)"
        ).fetchone()[0]
        >= 1
    )
    connection.close()


def test_generated_corpora_have_no_duplicate_or_conflicting_texts(tmp_path):
    generate_dev_corpus(tmp_path)
    ood = generate_ood_corpus(tmp_path)
    import pandas as pd
    from sklearn.model_selection import StratifiedGroupKFold

    development = pd.read_csv(tmp_path / "corpus_dev.csv")
    ood_frame = pd.read_csv(tmp_path / "corpus_ood.csv")
    assert len(development) == 2_000
    assert development["text"].is_unique
    assert development.groupby("text")["label"].nunique().max() == 1
    assert ood_frame["text"].is_unique
    assert {"text", "label", "group"} <= set(development.columns)
    assert set(ood_frame["kind"]) == {"ood", "regra"}
    assert not set(development["text"]) & set(ood_frame["text"])
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    for training_indices, validation_indices in splitter.split(
        development["text"],
        development["label"],
        groups=development["group"],
    ):
        training_groups = set(development.iloc[training_indices]["group"])
        validation_groups = set(development.iloc[validation_indices]["group"])
        assert not training_groups & validation_groups
    assert len(ood) == len(ood_frame)
