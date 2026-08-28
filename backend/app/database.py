from pathlib import Path
import json
import sqlite3

from .models import CostRecord, Finding, ResourceRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS costs (
  usage_date TEXT NOT NULL,
  service TEXT NOT NULL,
  amount REAL NOT NULL,
  account_id TEXT NOT NULL,
  region TEXT NOT NULL,
  PRIMARY KEY (usage_date, service, account_id, region)
);
CREATE TABLE IF NOT EXISTS resources (
  resource_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  collected_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings (
  finding_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  status TEXT NOT NULL,
  detected_at TEXT NOT NULL
);
"""


class Repository:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def replace_snapshot(self, costs: list[CostRecord], resources: list[ResourceRecord], findings: list[Finding]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """INSERT OR REPLACE INTO costs (usage_date, service, amount, account_id, region)
                   VALUES (?, ?, ?, ?, ?)""",
                [(str(item.date), item.service, item.amount, item.account_id, item.region) for item in costs],
            )
            connection.executemany(
                "INSERT OR REPLACE INTO resources (resource_id, payload, collected_at) VALUES (?, ?, ?)",
                [(item.resource_id, item.model_dump_json(), item.collected_at.isoformat()) for item in resources],
            )
            connection.executemany(
                "INSERT OR REPLACE INTO findings (finding_id, payload, status, detected_at) VALUES (?, ?, ?, ?)",
                [(item.id, item.model_dump_json(), item.status, item.detected_at.isoformat()) for item in findings],
            )

    def list_costs(self) -> list[CostRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT usage_date, service, amount, account_id, region FROM costs ORDER BY usage_date, service"
            ).fetchall()
        return [CostRecord(date=row["usage_date"], service=row["service"], amount=row["amount"], account_id=row["account_id"], region=row["region"]) for row in rows]

    def list_resources(self) -> list[ResourceRecord]:
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM resources ORDER BY resource_id").fetchall()
        return [ResourceRecord.model_validate(json.loads(row["payload"])) for row in rows]

    def list_findings(self) -> list[Finding]:
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM findings ORDER BY detected_at DESC").fetchall()
        return [Finding.model_validate(json.loads(row["payload"])) for row in rows]


class PostgresRepository:
    def __init__(self, database_url: str):
        import psycopg

        self.database_url = database_url
        with psycopg.connect(database_url) as connection:
            connection.execute(SCHEMA)

    def connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.database_url, row_factory=dict_row)

    def replace_snapshot(self, costs: list[CostRecord], resources: list[ResourceRecord], findings: list[Finding]) -> None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO costs (usage_date, service, amount, account_id, region)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (usage_date, service, account_id, region)
                       DO UPDATE SET amount = EXCLUDED.amount""",
                    [(str(item.date), item.service, item.amount, item.account_id, item.region) for item in costs],
                )
                cursor.executemany(
                    """INSERT INTO resources (resource_id, payload, collected_at) VALUES (%s, %s, %s)
                       ON CONFLICT (resource_id) DO UPDATE SET payload = EXCLUDED.payload, collected_at = EXCLUDED.collected_at""",
                    [(item.resource_id, item.model_dump_json(), item.collected_at.isoformat()) for item in resources],
                )
                cursor.executemany(
                    """INSERT INTO findings (finding_id, payload, status, detected_at) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (finding_id) DO UPDATE SET payload = EXCLUDED.payload, status = EXCLUDED.status, detected_at = EXCLUDED.detected_at""",
                    [(item.id, item.model_dump_json(), item.status, item.detected_at.isoformat()) for item in findings],
                )

    def list_costs(self) -> list[CostRecord]:
        with self.connect() as connection:
            rows = connection.execute("SELECT usage_date, service, amount, account_id, region FROM costs ORDER BY usage_date, service").fetchall()
        return [CostRecord(date=row["usage_date"], service=row["service"], amount=row["amount"], account_id=row["account_id"], region=row["region"]) for row in rows]

    def list_resources(self) -> list[ResourceRecord]:
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM resources ORDER BY resource_id").fetchall()
        return [ResourceRecord.model_validate(json.loads(row["payload"])) for row in rows]

    def list_findings(self) -> list[Finding]:
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM findings ORDER BY detected_at DESC").fetchall()
        return [Finding.model_validate(json.loads(row["payload"])) for row in rows]


def create_repository(database_path: str, database_url: str | None = None):
    if database_url:
        return PostgresRepository(database_url)
    return Repository(database_path)
