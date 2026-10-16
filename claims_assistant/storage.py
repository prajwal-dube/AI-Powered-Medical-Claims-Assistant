import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import ClaimResult, ExtractedClaim, Flag


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("""CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY, filename TEXT NOT NULL, extractor TEXT NOT NULL,
        prompt_version TEXT NOT NULL, fields TEXT NOT NULL, flags TEXT NOT NULL,
        fingerprint TEXT, created_at TEXT NOT NULL)""")
    connection.execute("CREATE INDEX IF NOT EXISTS claims_fingerprint ON claims(fingerprint)")
    return connection


def fingerprint(claim: ExtractedClaim) -> str | None:
    if not all([claim.patient_id, claim.diagnosis, claim.procedure,
                claim.amount is not None, claim.service_date]):
        return None
    values = [claim.patient_id, claim.diagnosis, claim.procedure, str(claim.amount.normalize()), claim.service_date]
    normalized = "|".join(str(value).strip().casefold() for value in values)
    return hashlib.sha256(normalized.encode()).hexdigest()


def insert_claim(path: str, filename: str, extractor: str, version: str,
                 claim: ExtractedClaim, review_fn) -> ClaimResult:
    digest = fingerprint(claim)
    with connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        duplicate = bool(digest and connection.execute(
            "SELECT 1 FROM claims WHERE fingerprint=? LIMIT 1", (digest,)).fetchone())
        flags = review_fn(claim, duplicate)
        created = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            "INSERT INTO claims(filename,extractor,prompt_version,fields,flags,fingerprint,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (filename, extractor, version, claim.model_dump_json(),
             json.dumps([flag.model_dump() for flag in flags]), digest, created))
        return ClaimResult(id=cursor.lastrowid, filename=filename, extractor=extractor,
                           prompt_version=version, fields=claim, flags=flags, created_at=created)


def list_claims(path: str, limit: int = 100) -> list[ClaimResult]:
    with connect(path) as connection:
        rows = connection.execute("SELECT * FROM claims ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [ClaimResult(id=row["id"], filename=row["filename"], extractor=row["extractor"],
                        prompt_version=row["prompt_version"],
                        fields=ExtractedClaim.model_validate_json(row["fields"]),
                        flags=[Flag.model_validate(item) for item in json.loads(row["flags"])],
                        created_at=row["created_at"]) for row in rows]
