from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import Listing

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    dedup_key     TEXT PRIMARY KEY,
    source_id     TEXT NOT NULL,
    notified      INTEGER NOT NULL DEFAULT 0,
    score         REAL,
    reasons       TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL,
    data          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source_id);
"""


class ListingStore:
    """Stockage SQLite des annonces vues (dédup par dedup_key)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        for col, decl in (("score", "REAL"), ("reasons", "TEXT")):
            try:
                self._conn.execute(f"ALTER TABLE listings ADD COLUMN {col} {decl}")
            except sqlite3.OperationalError:
                pass  # colonne déjà présente (base existante)

    def save(self, listing: Listing) -> bool:
        """Insère ou met à jour. Retourne True si l'annonce est nouvelle."""
        key = listing.dedup_key
        row = self._conn.execute(
            "SELECT dedup_key FROM listings WHERE dedup_key = ?", (key,)
        ).fetchone()
        listing.last_seen_at = datetime.now(UTC)
        payload = listing.model_dump_json()
        if row is None:
            self._conn.execute(
                "INSERT INTO listings"
                " (dedup_key, source_id, notified, first_seen_at, last_seen_at, data)"
                " VALUES (?, ?, 0, ?, ?, ?)",
                (
                    key,
                    listing.source_id,
                    listing.first_seen_at.isoformat(),
                    listing.last_seen_at.isoformat(),
                    payload,
                ),
            )
            self._conn.commit()
            return True
        self._conn.execute(
            "UPDATE listings SET last_seen_at = ?, data = ? WHERE dedup_key = ?",
            (listing.last_seen_at.isoformat(), payload, key),
        )
        self._conn.commit()
        return False

    def mark_notified(self, items: list[tuple[str, float, str]]) -> None:
        """items = liste de (dedup_key, score, reasons_json)."""
        self._conn.executemany(
            "UPDATE listings SET notified = 1, score = ?, reasons = ? WHERE dedup_key = ?",
            [(score, reasons, key) for key, score, reasons in items],
        )
        self._conn.commit()

    def recent_matches(self, limit: int = 30) -> list[dict]:
        rows = self._conn.execute(
            "SELECT data, score, reasons, first_seen_at FROM listings"
            " WHERE notified = 1 ORDER BY first_seen_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "listing": Listing.model_validate(json.loads(r["data"])),
                "score": r["score"],
                "reasons": json.loads(r["reasons"] or "[]"),
                "first_seen_at": r["first_seen_at"],
            }
            for r in rows
        ]

    def recent_pool(self, days: int = 30) -> list[Listing]:
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        rows = self._conn.execute(
            "SELECT data FROM listings WHERE first_seen_at >= ?", (cutoff,)
        ).fetchall()
        return [Listing.model_validate(json.loads(r["data"])) for r in rows]

    def stats(self) -> dict:
        total = self.count()
        notified = int(
            self._conn.execute("SELECT COUNT(*) AS n FROM listings WHERE notified = 1").fetchone()[
                "n"
            ]
        )
        return {"total": total, "notified": notified}

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS n FROM listings").fetchone()["n"])

    def close(self) -> None:
        self._conn.close()
