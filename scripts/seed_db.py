import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def create_database(data_dir, filename, schema, tables):
    database_path = data_dir / filename
    if database_path.exists():
        database_path.unlink()
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(schema)
        for table_name, rows in tables:
            if rows:
                placeholders = ",".join("?" for _ in rows[0])
                connection.executemany(
                    f"INSERT INTO {table_name} VALUES ({placeholders})",
                    rows,
                )
        connection.commit()
    finally:
        connection.close()


def seed_tms(now, data_dir):
    carriers = [
        (identifier, f"Transportadora {identifier:02d}") for identifier in range(1, 31)
    ]
    shipments = [
        (
            f"EMB{identifier:06d}",
            "agendado" if identifier % 3 == 0 else "em_transito",
            f"ABC{identifier % 100:04d}",
            (identifier % 30) + 1,
            (identifier % 10) + 1,
            now.date().isoformat(),
        )
        for identifier in range(1, 501)
    ]
    invoices = [("123456", "EMB000010")]
    invoices.extend(
        (
            str(100000 + identifier),
            f"EMB{identifier % 499 + 1:06d}",
        )
        for identifier in range(1, 1500)
    )
    appointments = [
        (
            f"EMB{identifier:06d}",
            (now + timedelta(days=1))
            .replace(hour=8, minute=0, second=0, microsecond=0)
            .isoformat(),
            identifier % 10 + 1,
            "confirmado",
        )
        for identifier in range(1, 501)
    ]
    create_database(
        data_dir,
        "tms.db",
        """
        CREATE TABLE transportadoras(
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL
        );
        CREATE TABLE embarques(
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            placa TEXT NOT NULL,
            transportadora_id INTEGER NOT NULL,
            doca INTEGER NOT NULL,
            data TEXT NOT NULL
        );
        CREATE TABLE notas_fiscais(
            numero TEXT NOT NULL,
            embarque_id TEXT NOT NULL
        );
        CREATE TABLE agendamentos(
            embarque_id TEXT NOT NULL,
            data TEXT NOT NULL,
            doca INTEGER NOT NULL,
            status TEXT NOT NULL
        );
        """,
        [
            ("transportadoras", carriers),
            ("embarques", shipments),
            ("notas_fiscais", invoices),
            ("agendamentos", appointments),
        ],
    )


def seed_yard(now, data_dir):
    movements = [
        (
            f"ABC{identifier % 100:04d}",
            f"EMB{identifier:06d}",
            (now - timedelta(hours=identifier % 4)).isoformat(),
            (now - timedelta(hours=max(identifier % 4 - 1, 0))).isoformat(),
            None,
        )
        for identifier in range(1, 501)
    ]
    movements[0] = (
        "AAA-1234",
        "EMB000001",
        (now - timedelta(hours=6)).isoformat(),
        (now - timedelta(hours=5)).isoformat(),
        None,
    )
    movements[1] = (
        "AAA1B23",
        "EMB000002",
        (now - timedelta(hours=2)).isoformat(),
        None,
        None,
    )
    movements[2] = (
        "ABC1D23",
        "EMB000003",
        (now - timedelta(hours=7)).isoformat(),
        (now - timedelta(hours=6)).isoformat(),
        None,
    )
    movements[3] = (
        "ABC0004",
        "EMB000004",
        (now - timedelta(hours=8)).isoformat(),
        (now - timedelta(hours=7)).isoformat(),
        (now - timedelta(hours=1)).isoformat(),
    )
    create_database(
        data_dir,
        "patio.db",
        """
        CREATE TABLE movimentacao(
            placa TEXT NOT NULL,
            embarque TEXT NOT NULL,
            chegada_portaria TEXT,
            entrada_doca TEXT,
            saida TEXT
        );
        """,
        [("movimentacao", movements)],
    )


def seed_occurrences(data_dir):
    occurrences = [
        (
            f"EMB{identifier:06d}",
            "avaria" if identifier % 4 == 0 else "atraso",
            "Registro operacional sintético",
        )
        for identifier in range(1, 501)
    ]
    create_database(
        data_dir,
        "ocorrencias.db",
        """
        CREATE TABLE ocorrencias(
            embarque TEXT NOT NULL,
            tipo TEXT NOT NULL,
            descricao TEXT NOT NULL
        );
        """,
        [("ocorrencias", occurrences)],
    )


def seed_application(data_dir):
    create_database(
        data_dir,
        "app.db",
        """
        CREATE TABLE usuarios(
            chat_id INTEGER PRIMARY KEY,
            perfil TEXT NOT NULL CHECK(
                perfil IN ('interno', 'transportadora', 'motorista')
            ),
            transportadora_id INTEGER,
            placa TEXT
        );
        CREATE TABLE auditoria(
            timestamp TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            perfil TEXT,
            masked_text TEXT NOT NULL,
            intent TEXT NOT NULL,
            probability REAL NOT NULL,
            result TEXT NOT NULL
        );
        """,
        [
            (
                "usuarios",
                [
                    (1, "interno", None, None),
                    (2, "transportadora", 1, None),
                    (3, "motorista", None, "AAA-1234"),
                ],
            )
        ],
    )


def seed_database(data_dir=DATA):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().replace(microsecond=0)
    seed_tms(now, data_dir)
    seed_yard(now, data_dir)
    seed_occurrences(data_dir)
    seed_application(data_dir)
    return data_dir


def main():
    parser = argparse.ArgumentParser(description="Gera bancos SQLite sintéticos.")
    parser.add_argument("--data-dir", type=Path, default=DATA)
    args = parser.parse_args()
    seed_database(args.data_dir)
    print(f"Bancos sintéticos criados em {args.data_dir}")


if __name__ == "__main__":
    main()
