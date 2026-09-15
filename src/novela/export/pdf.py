"""Derivado en PDF (BUILD_SPEC §12, §15).

Intenta Pandoc si esta en el PATH. Si no lo esta, genera un PDF minimo con una
funcion de respaldo y **nunca rompe el pipeline**: el Markdown ya es el
entregable canonico.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PAGE_WIDTH, PAGE_HEIGHT = 595, 842
MARGIN, LINE_HEIGHT, FONT_SIZE = 56, 15, 11
MAX_CHARS_PER_LINE = 92


@dataclass(frozen=True)
class PdfResult:
    path: Path | None
    engine: str
    message: str


def export_pdf(markdown_path: Path, pdf_path: Path) -> PdfResult:
    """Genera el PDF. Devuelve siempre un resultado; nunca lanza por falta de Pandoc."""
    if shutil.which("pandoc"):
        try:
            subprocess.run(
                ["pandoc", str(markdown_path), "-o", str(pdf_path)],
                check=True,
                capture_output=True,
                timeout=120,
            )
            return PdfResult(pdf_path, "pandoc", "PDF generado con Pandoc.")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            detail = getattr(error, "stderr", b"") or b""
            return _fallback(
                markdown_path,
                pdf_path,
                f"Pandoc ha fallado ({detail[:160].decode('utf-8', 'replace')}).",
            )
    return _fallback(
        markdown_path,
        pdf_path,
        "Pandoc no está en el PATH: se usa el generador de respaldo. "
        "Instala Pandoc para obtener un PDF con tipografía real.",
    )


def _wrap(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if not raw.strip():
            lines.append("")
            continue
        current = ""
        for word in raw.split():
            candidate = f"{current} {word}".strip()
            if len(candidate) > MAX_CHARS_PER_LINE:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def _escape(text: str) -> str:
    safe = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    return safe.encode("latin-1", "replace").decode("latin-1")


def _pages(lines: list[str]) -> list[list[str]]:
    per_page = (PAGE_HEIGHT - 2 * MARGIN) // LINE_HEIGHT
    return [lines[index : index + per_page] for index in range(0, len(lines), per_page)] or [[]]


def _fallback(markdown_path: Path, pdf_path: Path, message: str) -> PdfResult:
    """Escribe un PDF valido y minimo sin dependencias externas."""
    pages = _pages(_wrap(markdown_path.read_text(encoding="utf-8")))
    objects: list[bytes] = []
    page_ids = [4 + index * 2 for index in range(len(pages))]

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("latin-1"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for index, page in enumerate(pages):
        body = [f"BT /F1 {FONT_SIZE} Tf {MARGIN} {PAGE_HEIGHT - MARGIN} Td {LINE_HEIGHT} TL"]
        body.extend(f"({_escape(line)}) Tj T*" for line in page)
        body.append("ET")
        stream = "\n".join(body).encode("latin-1")
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_ids[index] + 1} 0 R >>"
            ).encode("latin-1")
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(_serialise(objects))
    return PdfResult(pdf_path, "fallback", message)


def _serialise(objects: list[bytes]) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, payload in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode("latin-1") + payload + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)
