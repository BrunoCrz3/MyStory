"""Ensamblado del manuscrito canonico (BUILD_SPEC §12).

`manuscrito.md` es la fuente canonica. PDF, DOCX y EPUB son derivados y nunca se
editan directamente.
"""

from __future__ import annotations

from pathlib import Path

from novela.models import ChapterVersion


def assemble(
    *,
    title: str,
    logline: str,
    chapters: list[ChapterVersion],
    titles: dict[str, str] | None = None,
) -> str:
    """Concatena las versiones vigentes en el Markdown canonico de §12."""
    resolved = titles or {}
    parts = [f"# {title}", "", f"> {logline}", "", "---", ""]
    for chapter in sorted(chapters, key=lambda item: item.number):
        heading = resolved.get(str(chapter.number), chapter.title)
        parts.append(f"## Capítulo {chapter.number} — {heading}")
        parts.append("")
        parts.append(chapter.text.strip("\n"))
        parts.append("")
    return "\n".join(parts).rstrip("\n") + "\n"


def write_manuscript(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
