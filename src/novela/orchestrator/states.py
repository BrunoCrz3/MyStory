"""Estados del proyecto y del capitulo (BUILD_SPEC §10.1).

Cada transicion se persiste ANTES y DESPUES de la llamada al LLM: el proceso debe
poder morir en cualquier punto y reanudarse sin repetir trabajo hecho.
"""

from __future__ import annotations

from enum import StrEnum


class ProjectState(StrEnum):
    DRAFT = "draft"
    BIBLE_GENERATING = "bible_generating"
    BIBLE_REVIEW = "bible_review"
    BIBLE_APPROVED = "bible_approved"
    OUTLINE_GENERATING = "outline_generating"
    OUTLINE_REVIEW = "outline_review"
    OUTLINE_APPROVED = "outline_approved"
    WRITING = "writing"
    GLOBAL_REVIEW = "global_review"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


class ChapterState(StrEnum):
    PLANNED = "planned"
    DRAFTING = "drafting"
    VALIDATING = "validating"
    REWRITING = "rewriting"
    PATCHING = "patching"
    POLISHING = "polishing"
    ARCHIVING = "archiving"
    DONE = "done"
    ESCALATED = "escalated"
