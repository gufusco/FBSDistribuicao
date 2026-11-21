import sqlite3
from datetime import datetime

import pytest

from fbs_bot.engine import Engine


@pytest.fixture
def engine(tmp_path):
    app = sqlite3.connect(tmp_path / "app.db")
    app.executescript(
        """
        CREATE TABLE usuarios(
            chat_id INTEGER PRIMARY KEY,
            perfil TEXT,
            transportadora_id INTEGER,
            placa TEXT
        );
        CREATE TABLE auditoria(
            timestamp TEXT,
            chat_id INTEGER,
            perfil TEXT,
            masked_text TEXT,
            intent TEXT,
            probability REAL,
            result TEXT
        );
        INSERT INTO usuarios VALUES (1, 'interno', NULL, NULL);
        INSERT INTO usuarios VALUES (2, 'transportadora', 1, NULL);
        INSERT INTO usuarios VALUES (3, 'motorista', NULL, 'AAA-1234');
        """
    )
    app.commit()
    app.close()

    tms = sqlite3.connect(tmp_path / "tms.db")
    tms.executescript(
        """
        CREATE TABLE transportadoras(id INTEGER PRIMARY KEY, nome TEXT);
        CREATE TABLE embarques(
            id TEXT PRIMARY KEY, status TEXT, placa TEXT,
            transportadora_id INTEGER, doca INTEGER, data TEXT
        );
        CREATE TABLE notas_fiscais(numero TEXT, embarque_id TEXT);
        CREATE TABLE agendamentos(
            embarque_id TEXT, data TEXT, doca INTEGER, status TEXT
        );
        INSERT INTO transportadoras VALUES (1, 'Transportadora 01');
        INSERT INTO transportadoras VALUES (2, 'Transportadora 02');
        INSERT INTO transportadoras VALUES (3, 'Transportadora 03');
        INSERT INTO embarques VALUES
            ('EMB000001', 'agendado', 'AAA-1234', 1, 1, '2026-11-20');
        INSERT INTO embarques VALUES
            ('EMB000002', 'em_transito', 'ABC-0005', 2, 2, '2026-11-20');
        INSERT INTO notas_fiscais VALUES ('654321', 'EMB000001');
        INSERT INTO notas_fiscais VALUES ('123456', 'EMB000002');
        INSERT INTO agendamentos VALUES
            ('EMB000001', '2026-11-22T08:00:00', 1, 'confirmado');
        INSERT INTO agendamentos VALUES
            ('EMB000002', '2026-11-22T09:00:00', 2, 'confirmado');
        """
    )
    tms.executemany(
        "INSERT INTO transportadoras VALUES (?, ?)",
        [
            (identifier, f"Transportadora {identifier:02d}")
            for identifier in range(4, 31)
        ],
    )
    tms.commit()
    tms.close()

    patio = sqlite3.connect(tmp_path / "patio.db")
    patio.executescript(
        """
        CREATE TABLE movimentacao(
            placa TEXT, embarque TEXT, chegada_portaria TEXT,
            entrada_doca TEXT, saida TEXT
        );
        INSERT INTO movimentacao VALUES
            ('AAA-1234', 'EMB000001', '2026-11-20T08:00:00',
             '2026-11-20T09:00:00', NULL);
        INSERT INTO movimentacao VALUES
            ('ABC-0005', 'EMB000002', '2026-11-20T08:00:00',
             '2026-11-20T09:00:00', NULL);
        """
    )
    patio.commit()
    patio.close()

    occ = sqlite3.connect(tmp_path / "ocorrencias.db")
    occ.executescript(
        """
        CREATE TABLE ocorrencias(embarque TEXT, tipo TEXT, descricao TEXT);
        INSERT INTO ocorrencias VALUES ('EMB000001', 'atraso', 'Teste');
        INSERT INTO ocorrencias VALUES ('EMB000002', 'avaria', 'Teste');
        """
    )
    occ.commit()
    occ.close()

    instance = Engine(
        data_dir=tmp_path,
        model_path=None,
        clock=lambda: 1_000,
        wall_clock=lambda: datetime(2026, 11, 21, 12, 0),
    )
    yield instance
    instance.conn.close()
