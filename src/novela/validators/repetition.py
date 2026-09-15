"""Validador de repeticion: 100 % determinista, sin LLM (BUILD_SPEC §9.4).

Contrato central: **un umbral `null` desactiva esa severidad, no la
comprobacion**. La metrica se calcula siempre y se registra en
`ValidationReport.metrics` para poder calibrar despues con datos.

Ningun umbral vive en este modulo: todos llegan en `RepetitionCfg` (§18).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from novela.config import RepetitionCfg
from novela.models import Severity, StyleArtifact
from novela.validators.base import ValidationReport, issue
from novela.validators.length import prose_lines

# Lista de palabras vacias del español. Se mantiene como texto para que sea
# legible y editable de un vistazo al calibrar.
_STOPWORD_TEXT = """
    a al algo algun alguna algunas alguno algunos ante antes aquel aquella aquellas aquello
    aquellos aqui asi aun aunque cada como con contra cual cuales cuando cuanto de del desde
    donde dos e el ella ellas ello ellos en entre era eran eres es esa esas ese eso esos esta
    estaba estaban estan estar estas este esto estos fue fueron ha habia han hasta hay la las
    le les lo los mas me mi mientras mis mucho muy nada ni no nos nosotros o os otra otras otro
    otros para pero poco por porque que quien quienes se sea segun ser si sin sobre solo son su
    sus tal tambien tan tanto te tiene tienen todo todos tras tu tus un una unas uno unos usted
    ustedes ya yo lel della dello puede pueden podia podian
    """
STOPWORDS: frozenset[str] = frozenset(_STOPWORD_TEXT.split())

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")
WORD_RE = re.compile(r"[a-záéíóúüñ0-9-]+")
DIALOGUE_OPENERS = ("—", "–", "-", "«", '"', "“", "'")
REFLECTION_MARKERS = frozenset(
    {"penso", "pense", "recordo", "recorde", "sabia", "quiza", "quizas", "tal", "acaso", "creyo"}
)
VERB_SUFFIXES = (
    "aba",
    "ia",
    "aron",
    "ieron",
    "aba",
    "o",
    "e",
    "io",
    "ar",
    "er",
    "ir",
    "ando",
    "iendo",
)
#: Coseno minimo para considerar que una imagen nueva reutiliza una ya registrada.
IMAGE_REUSE_COSINE = 0.90


def strip_accents(word: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", word) if unicodedata.category(char) != "Mn"
    )


def tokens(text: str) -> list[str]:
    """Palabras significativas: minusculas, sin acentos y sin vacias."""
    words = WORD_RE.findall(text.lower())
    return [plain for word in words if (plain := strip_accents(word)) not in STOPWORDS]


def ngrams(items: list[str], size: int) -> set[tuple[str, ...]]:
    return {tuple(items[index : index + size]) for index in range(len(items) - size + 1)}


def jaccard(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def cosine_max(text: str, others: list[str]) -> float:
    """Maxima similitud TF-IDF del texto frente a un corpus. 0.0 si no hay corpus util."""
    corpus = [item for item in others if item.strip()]
    if not corpus or not text.strip():
        return 0.0
    try:
        matrix = TfidfVectorizer().fit_transform([text, *corpus])
    except ValueError:
        # Vocabulario vacio tras el filtrado: no hay nada que comparar.
        return 0.0
    similarities = cosine_similarity(matrix[0:1], matrix[1:])
    return float(similarities.max())


def sentences(text: str) -> list[str]:
    parts: list[str] = []
    for line in prose_lines(text):
        parts.extend(chunk.strip() for chunk in SENTENCE_SPLIT_RE.split(line) if chunk.strip())
    return parts


def classify_opening(text: str) -> str:
    """Clasificacion por reglas del tipo de apertura de un capitulo (§9.4)."""
    first = next(iter(sentences(text)), "")
    if not first:
        return "vacia"
    if first.startswith(DIALOGUE_OPENERS):
        return "dialogo"
    words = WORD_RE.findall(first.lower())
    if not words:
        return "descripcion"
    if any(strip_accents(word) in REFLECTION_MARKERS for word in words):
        return "reflexion"
    head = strip_accents(words[0])
    if head not in STOPWORDS and head.endswith(VERB_SUFFIXES):
        return "accion"
    return "descripcion"


def sentence_openers(text: str, words: int = 3) -> list[str]:
    return [
        " ".join(strip_accents(word) for word in WORD_RE.findall(sentence.lower())[:words])
        for sentence in sentences(text)
    ]


def mtld(items: list[str], threshold: float = 0.72) -> float:
    """Diversidad lexica MTLD: longitud media de segmento antes de caer bajo el umbral."""
    if not items:
        return 0.0
    factors, start = 0.0, 0
    for index in range(len(items)):
        window = items[start : index + 1]
        if len(set(window)) / len(window) <= threshold:
            factors += 1
            start = index + 1
    remainder = items[start:]
    if remainder:
        ratio = len(set(remainder)) / len(remainder)
        factors += (1 - ratio) / (1 - threshold) if threshold < 1 else 0.0
    return len(items) / factors if factors else float(len(items))


def _threshold_severity(
    value: float, blocking: float | None, warning: float | None
) -> Severity | None:
    """Traduce una metrica a severidad. Un umbral `null` desactiva SOLO esa severidad."""
    if blocking is not None and value >= blocking:
        return Severity.BLOCKING
    if warning is not None and value >= warning:
        return Severity.MINOR
    return None


def _check_ngram_overlap(
    text: str, previous: list[str], cfg: RepetitionCfg, chapter: int, report: ValidationReport
) -> None:
    current = ngrams(tokens(text), cfg.ngram_size)
    best, best_index = 0.0, 0
    for index, other in enumerate(previous, start=1):
        score = jaccard(current, ngrams(tokens(other), cfg.ngram_size))
        if score > best:
            best, best_index = score, index
    report.metrics["rep.jaccard_max"] = round(best, 4)

    severity = _threshold_severity(best, cfg.jaccard_blocking, cfg.jaccard_warning)
    if severity is None:
        return
    report.issues.append(
        issue(
            "REP-NGRAM",
            f"Solapamiento de {cfg.ngram_size}-gramas de {best:.2f} con el capítulo "
            f"{best_index}. Reescribe las frases coincidentes con imágenes y sintaxis nuevas.",
            chapter=chapter,
            severity=severity,
            evidence=f"jaccard={best:.4f}",
        )
    )


def _check_cosine(
    text: str, previous: list[str], cfg: RepetitionCfg, chapter: int, report: ValidationReport
) -> None:
    best = cosine_max(text, previous)
    report.metrics["rep.cosine_max"] = round(best, 4)
    severity = _threshold_severity(best, cfg.cosine_scene_blocking, cfg.cosine_scene_warning)
    if severity is None:
        return
    report.issues.append(
        issue(
            "REP-COSINE",
            f"Similitud semántica de {best:.2f} con un capítulo anterior: la escena repite "
            "contenido ya narrado. Cambia el foco, el conflicto o el punto de entrada.",
            chapter=chapter,
            severity=severity,
            evidence=f"cosine={best:.4f}",
        )
    )


def _check_image_reuse(
    text: str, artifacts: list[StyleArtifact], chapter: int, report: ValidationReport
) -> None:
    images = [item for item in artifacts if item.kind in {"metafora", "imagen"}]
    best = 0.0
    worst: StyleArtifact | None = None
    for sentence in sentences(text):
        for artifact in images:
            score = cosine_max(sentence, [artifact.text])
            if score > best:
                best, worst = score, artifact
    report.metrics["rep.image_cosine_max"] = round(best, 4)
    if worst is None or best <= IMAGE_REUSE_COSINE:
        return
    report.issues.append(
        issue(
            "REP-IMAGE-REUSE",
            f"El capítulo reutiliza una imagen ya usada en el capítulo {worst.chapter}. "
            "Sustitúyela por una imagen nueva del mismo campo semántico.",
            chapter=chapter,
            evidence=worst.text,
        )
    )


def _check_trigram_tics(
    text: str, previous: list[str], cfg: RepetitionCfg, chapter: int, report: ValidationReport
) -> None:
    counts = Counter[tuple[str, ...]]()
    for item in [*previous, text]:
        counts.update(ngrams(tokens(item), 3))
    top = counts.most_common(1)
    worst = top[0][1] if top else 0
    report.metrics["rep.trigram_max_repeats"] = float(worst)
    if worst <= cfg.max_trigram_repeats:
        return
    phrase = " ".join(top[0][0])
    report.issues.append(
        issue(
            "REP-NGRAM",
            f"La expresión «{phrase}» aparece {worst} veces en el manuscrito y el perfil admite "
            f"{cfg.max_trigram_repeats}. Es una muletilla: elimínala de este capítulo.",
            chapter=chapter,
            severity=Severity.MINOR,
            evidence=phrase,
        )
    )


def _check_opening_type(
    text: str, history: list[str], cfg: RepetitionCfg, chapter: int, report: ValidationReport
) -> None:
    kind = classify_opening(text)
    window = history[-cfg.opening_type_window :] if cfg.opening_type_window else []
    report.metrics["rep.opening_repeated"] = float(kind in window)
    if kind not in window:
        return
    report.issues.append(
        issue(
            "REP-OPENING-TYPE",
            f"El capítulo abre con el tipo «{kind}», ya usado en los últimos "
            f"{cfg.opening_type_window} capítulos. Cambia el punto de entrada de la escena.",
            chapter=chapter,
            evidence=kind,
        )
    )


def _check_sentence_openers(
    text: str, seen: set[str], cfg: RepetitionCfg, chapter: int, report: ValidationReport
) -> None:
    openers = sentence_openers(text)
    repeated = sorted({opener for opener in openers if opener and opener in seen})
    counts = Counter(opener for opener in openers if opener)
    repeated.extend(sorted(opener for opener, count in counts.items() if count > 1))
    report.metrics["rep.sentence_openers_repeated"] = float(len(set(repeated)))
    if not cfg.forbid_reused_sentence_openers or not repeated:
        return
    report.issues.append(
        issue(
            "REP-SENTENCE-OPENER",
            f"Arranques de frase ya utilizados: {', '.join(sorted(set(repeated))[:3])}. "
            "Varía el sujeto o el orden de la frase.",
            chapter=chapter,
            evidence="; ".join(sorted(set(repeated))[:5]),
        )
    )


def _check_lexical_diversity(
    text: str, previous: list[str], cfg: RepetitionCfg, chapter: int, report: ValidationReport
) -> None:
    current = mtld(tokens(text))
    report.metrics["rep.mtld"] = round(current, 3)
    if not cfg.mtld_check or cfg.mtld_drop_max is None or not previous:
        return
    baseline = sum(mtld(tokens(item)) for item in previous) / len(previous)
    if baseline <= 0:
        return
    drop = (baseline - current) / baseline
    report.metrics["rep.mtld_drop"] = round(drop, 4)
    if drop <= cfg.mtld_drop_max:
        return
    report.issues.append(
        issue(
            "REP-LEXICAL-DIVERSITY",
            f"La diversidad léxica cae un {drop:.0%} respecto a la media previa "
            f"(máximo admitido {cfg.mtld_drop_max:.0%}). La prosa se está volviendo monótona.",
            chapter=chapter,
            evidence=f"mtld={current:.1f} vs {baseline:.1f}",
        )
    )


def validate(
    text: str,
    *,
    previous_texts: list[str],
    style_artifacts: list[StyleArtifact],
    opening_history: list[str],
    seen_openers: set[str],
    cfg: RepetitionCfg,
    chapter: int,
) -> ValidationReport:
    """Ejecuta las siete comprobaciones de §9.4. Todas dejan metrica; no todas emiten."""
    report = ValidationReport()
    _check_ngram_overlap(text, previous_texts, cfg, chapter, report)
    _check_cosine(text, previous_texts, cfg, chapter, report)
    _check_image_reuse(text, style_artifacts, chapter, report)
    _check_trigram_tics(text, previous_texts, cfg, chapter, report)
    _check_opening_type(text, opening_history, cfg, chapter, report)
    _check_sentence_openers(text, seen_openers, cfg, chapter, report)
    _check_lexical_diversity(text, previous_texts, cfg, chapter, report)
    return report
