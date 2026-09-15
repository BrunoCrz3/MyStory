"""Persistencia: SQLite como fuente de verdad, artefactos JSON/MD espejados a disco.

Reglas duras (BUILD_SPEC §2.1, §10.2, §26.2):

- El estado del mundo lo escribe UNICAMENTE `commit_chapter`, en una unica
  transaccion por capitulo.
- Los hechos se revocan, no se borran.
- La interfaz `Store` queda abstracta para poder sustituir SQLite por Postgres
  sin tocar nada aguas arriba.
"""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from novela.errors import StoreError
from novela.models import (
    ArchivistOutput,
    ChapterSummary,
    ChapterVersion,
    Ledger,
    Outline,
    StoryBible,
    StyleArtifact,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
    id TEXT PRIMARY KEY,
    premise TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifact (
    name TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chapter (
    number INTEGER PRIMARY KEY,
    state TEXT NOT NULL,
    stale INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS chapter_version (
    number INTEGER NOT NULL,
    version INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (number, version)
);
CREATE TABLE IF NOT EXISTS fact (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS thread (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS summary (
    number INTEGER PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS style_artifact (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
"""


def _dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


class Store(ABC):
    """Contrato de persistencia del harness."""

    @abstractmethod
    def create_project(self, premise: str, state: str) -> None: ...

    @abstractmethod
    def project_state(self) -> str: ...

    @abstractmethod
    def set_project_state(self, state: str) -> None: ...

    @abstractmethod
    def premise(self) -> str: ...

    @abstractmethod
    def save_bible(self, bible: StoryBible) -> None: ...

    @abstractmethod
    def load_bible(self) -> StoryBible | None: ...

    @abstractmethod
    def save_outline(self, outline: Outline) -> None: ...

    @abstractmethod
    def load_outline(self) -> Outline | None: ...

    @abstractmethod
    def load_ledger(self) -> Ledger: ...

    @abstractmethod
    def load_summaries(self) -> list[ChapterSummary]: ...

    @abstractmethod
    def load_style_artifacts(self) -> list[StyleArtifact]: ...

    @abstractmethod
    def chapter_state(self, number: int) -> str | None: ...

    @abstractmethod
    def set_chapter_state(self, number: int, state: str, *, stale: bool = False) -> None: ...

    @abstractmethod
    def chapter_versions(self, number: int) -> list[ChapterVersion]: ...

    @abstractmethod
    def latest_chapter(self, number: int) -> ChapterVersion | None: ...

    @abstractmethod
    def commit_chapter(
        self, number: int, version: ChapterVersion, archivist: ArchivistOutput, state: str
    ) -> None: ...


class SQLiteStore(Store):
    """Implementacion sobre SQLite con espejo de artefactos en `out/<pid>/`."""

    def __init__(self, project_id: str, directory: Path) -> None:
        self.project_id = project_id
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / "chapters").mkdir(exist_ok=True)
        (self.directory / "reports").mkdir(exist_ok=True)
        self.db_path = self.directory / "project.db"
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    # ---------------- proyecto ----------------
    def create_project(self, premise: str, state: str) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO project (id, premise, state, created_at) VALUES (?, ?, ?, ?)",
            (self.project_id, premise, state, datetime.now(UTC).isoformat()),
        )
        self.connection.commit()

    def _project_row(self) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM project WHERE id = ?", (self.project_id,)
        ).fetchone()
        if row is None:
            raise StoreError(
                f"el proyecto '{self.project_id}' no existe en {self.db_path}. "
                "Crealo con `novela init`."
            )
        return row

    def project_state(self) -> str:
        return str(self._project_row()["state"])

    def premise(self) -> str:
        return str(self._project_row()["premise"])

    def set_project_state(self, state: str) -> None:
        self.connection.execute(
            "UPDATE project SET state = ? WHERE id = ?", (state, self.project_id)
        )
        self.connection.commit()

    # ---------------- artefactos simples ----------------
    def _save_artifact(self, name: str, payload: Any, filename: str | None) -> None:
        """Persiste en SQLite y, si `filename` no es None, espeja el artefacto a disco."""
        self.connection.execute(
            "INSERT OR REPLACE INTO artifact (name, payload, updated_at) VALUES (?, ?, ?)",
            (name, _dumps(payload), datetime.now(UTC).isoformat()),
        )
        self.connection.commit()
        if filename is not None:
            (self.directory / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    def _load_artifact(self, name: str) -> Any | None:
        row = self.connection.execute(
            "SELECT payload FROM artifact WHERE name = ?", (name,)
        ).fetchone()
        return None if row is None else json.loads(row["payload"])

    def save_bible(self, bible: StoryBible) -> None:
        self._save_artifact("bible", bible.model_dump(mode="json"), "bible.json")

    def load_bible(self) -> StoryBible | None:
        payload = self._load_artifact("bible")
        return None if payload is None else StoryBible.model_validate(payload)

    def save_outline(self, outline: Outline) -> None:
        self._save_artifact("outline", outline.model_dump(mode="json"), "outline.json")

    def load_outline(self) -> Outline | None:
        payload = self._load_artifact("outline")
        return None if payload is None else Outline.model_validate(payload)

    def save_report(self, name: str, payload: Any) -> None:
        path = self.directory / "reports" / f"{name}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # ---------------- estado del mundo ----------------
    def load_ledger(self) -> Ledger:
        facts = [
            json.loads(row["payload"])
            for row in self.connection.execute("SELECT payload FROM fact ORDER BY id")
        ]
        threads = [
            json.loads(row["payload"])
            for row in self.connection.execute("SELECT payload FROM thread ORDER BY id")
        ]
        stored = self._load_artifact("ledger_meta") or {}
        return Ledger.model_validate(
            {
                "facts": facts,
                "threads": threads,
                "entities": stored.get("entities", []),
                "timeline": stored.get("timeline", []),
            }
        )

    def load_summaries(self) -> list[ChapterSummary]:
        return [
            ChapterSummary.model_validate(json.loads(row["payload"]))
            for row in self.connection.execute("SELECT payload FROM summary ORDER BY number")
        ]

    def load_style_artifacts(self) -> list[StyleArtifact]:
        return [
            StyleArtifact.model_validate(json.loads(row["payload"]))
            for row in self.connection.execute("SELECT payload FROM style_artifact ORDER BY id")
        ]

    # ---------------- capitulos ----------------
    def chapter_state(self, number: int) -> str | None:
        row = self.connection.execute(
            "SELECT state FROM chapter WHERE number = ?", (number,)
        ).fetchone()
        return None if row is None else str(row["state"])

    def set_chapter_state(self, number: int, state: str, *, stale: bool = False) -> None:
        self.connection.execute(
            "INSERT INTO chapter (number, state, stale) VALUES (?, ?, ?) "
            "ON CONFLICT(number) DO UPDATE SET state = excluded.state, stale = excluded.stale",
            (number, state, int(stale)),
        )
        self.connection.commit()

    def stale_chapters(self) -> list[int]:
        return [
            int(row["number"])
            for row in self.connection.execute(
                "SELECT number FROM chapter WHERE stale = 1 ORDER BY number"
            )
        ]

    def mark_all_stale(self) -> None:
        self.connection.execute("UPDATE chapter SET stale = 1")
        self.connection.commit()

    def chapter_versions(self, number: int) -> list[ChapterVersion]:
        return [
            ChapterVersion.model_validate(json.loads(row["payload"]))
            for row in self.connection.execute(
                "SELECT payload FROM chapter_version WHERE number = ? ORDER BY version", (number,)
            )
        ]

    def latest_chapter(self, number: int) -> ChapterVersion | None:
        versions = self.chapter_versions(number)
        return versions[-1] if versions else None

    def all_chapters(self) -> list[ChapterVersion]:
        numbers = [
            int(row["number"])
            for row in self.connection.execute("SELECT number FROM chapter ORDER BY number")
        ]
        return [version for number in numbers if (version := self.latest_chapter(number))]

    def commit_chapter(
        self, number: int, version: ChapterVersion, archivist: ArchivistOutput, state: str
    ) -> None:
        """Unica escritura del estado del mundo. Atomica: o entra todo, o no entra nada."""
        next_version = len(self.chapter_versions(number)) + 1
        stored = version.model_copy(update={"version": next_version})
        try:
            with self.connection:
                self.connection.execute(
                    "INSERT INTO chapter_version (number, version, payload) VALUES (?, ?, ?)",
                    (number, next_version, _dumps(stored.model_dump(mode="json"))),
                )
                self.connection.execute(
                    "INSERT INTO chapter (number, state, stale) VALUES (?, ?, 0) "
                    "ON CONFLICT(number) DO UPDATE SET state = excluded.state, stale = 0",
                    (number, state),
                )
                for fact in archivist.facts:
                    self.connection.execute(
                        "INSERT OR REPLACE INTO fact (id, payload) VALUES (?, ?)",
                        (fact.id, _dumps(fact.model_dump(mode="json"))),
                    )
                for thread in archivist.threads:
                    self.connection.execute(
                        "INSERT OR REPLACE INTO thread (id, payload) VALUES (?, ?)",
                        (thread.id, _dumps(thread.model_dump(mode="json"))),
                    )
                self.connection.execute(
                    "INSERT OR REPLACE INTO summary (number, payload) VALUES (?, ?)",
                    (number, _dumps(archivist.summary.model_dump(mode="json"))),
                )
                for artifact in archivist.style_artifacts:
                    self.connection.execute(
                        "INSERT OR REPLACE INTO style_artifact (id, payload) VALUES (?, ?)",
                        (artifact.id, _dumps(artifact.model_dump(mode="json"))),
                    )
        except sqlite3.Error as error:
            raise StoreError(f"no se ha podido consolidar el capitulo {number}: {error}") from error

        self._mirror_chapter(number, stored, archivist)

    def _mirror_chapter(
        self, number: int, version: ChapterVersion, archivist: ArchivistOutput
    ) -> None:
        chapters = self.directory / "chapters"
        (chapters / f"ch_{number:02d}.md").write_text(
            f"## Capítulo {number} — {version.title}\n\n{version.text.rstrip()}\n", encoding="utf-8"
        )
        (chapters / f"ch_{number:02d}.versions.json").write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in self.chapter_versions(number)],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        ledger = self.load_ledger()
        entities = sorted(set(ledger.entities) | set(archivist.new_entities))
        timeline = [*ledger.timeline, archivist.summary.one_line]
        # ledger_meta es estado interno: vive en SQLite y se refleja dentro de
        # ledger.json, no como un fichero propio del inventario de §23.
        self._save_artifact("ledger_meta", {"entities": entities, "timeline": timeline}, None)
        refreshed = self.load_ledger().model_copy(update={"entities": entities, "timeline": timeline})
        (self.directory / "ledger.json").write_text(
            json.dumps(refreshed.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.directory / "summaries.json").write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in self.load_summaries()],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.directory / "style_artifacts.json").write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in self.load_style_artifacts()],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
