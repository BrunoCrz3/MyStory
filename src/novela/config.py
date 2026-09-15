"""Resolucion de configuracion (BUILD_SPEC §3).

Este es el UNICO modulo del sistema que lee ficheros YAML, variables de entorno
o flags de la CLI. Todos los demas reciben un objeto `Config` ya resuelto.

Precedencia, de menor a mayor prioridad:

    1. config/default.yaml
    2. config/profiles/<profile>.yaml
    3. novela.yaml
    4. out/<pid>/config.yaml
    5. Variables de entorno NOVELA__*
    6. Flags de la CLI

La fusion es profunda por clave. Cada hoja recuerda de que fuente vino, para
que `novela config show --resolved` pueda explicar por que un valor es el que es.
"""

from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from novela.errors import ConfigError
from novela.models import LengthSpec

ENV_PREFIX = "NOVELA__"

#: Roles que comparten la configuracion de modelo de otro rol. El Parcheador usa
#: el modelo del Reescritor (§7) pero conserva etiqueta propia en `trace.jsonl` y
#: clave propia en las fixtures, para poder distinguir parche de reescritura.
ROLE_ALIASES: dict[str, str] = {"patcher": "rewriter"}
STRICT = ConfigDict(extra="forbid")

JsonDict = dict[str, Any]


# --------------------------------------------------------------------------
# Modelos de configuracion
# --------------------------------------------------------------------------
class ProjectCfg(BaseModel):
    model_config = STRICT

    language: str = "es"
    seed: int = 20260915


class NovelCfg(BaseModel):
    model_config = STRICT

    chapters: int = Field(ge=3, le=60)
    length: LengthSpec
    subgenre: str
    tone: str
    pov: str
    tense: str
    structure: str
    hardness: str
    forbidden: list[str] = Field(default_factory=list)


class ModelCfg(BaseModel):
    model_config = STRICT

    name: str
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(gt=0)


class OpenRouterCfg(BaseModel):
    model_config = STRICT

    base_url: str
    app_title: str
    app_referer: str
    require_parameters: bool = True
    allow_fallbacks: bool = False
    data_collection: Literal["deny", "allow"] = "deny"
    provider_order: list[str] = Field(default_factory=list)


class LLMCfg(BaseModel):
    model_config = STRICT

    provider: Literal["fake", "anthropic", "openrouter"]
    models: dict[str, ModelCfg]
    openrouter: OpenRouterCfg


class LimitsCfg(BaseModel):
    model_config = STRICT

    max_rewrite_attempts: int = Field(ge=1)
    max_schema_retries: int = Field(ge=1)
    max_cost_usd: float = Field(gt=0)
    context_token_budget: int = Field(gt=0)


class ApprovalCfg(BaseModel):
    model_config = STRICT

    bible: Literal["auto", "manual"] = "auto"
    outline: Literal["auto", "manual"] = "auto"
    final: Literal["auto", "manual"] = "auto"


class RepetitionCfg(BaseModel):
    """Umbrales de repeticion. Un umbral `null` desactiva esa severidad, nunca el calculo."""

    model_config = STRICT

    ngram_size: int = Field(ge=2, le=8)
    jaccard_blocking: float | None = None
    jaccard_warning: float | None = None
    cosine_scene_blocking: float | None = None
    cosine_scene_warning: float | None = None
    max_trigram_repeats: int = Field(ge=1)
    mtld_check: bool = False
    mtld_drop_max: float | None = None
    opening_type_window: int = Field(ge=0)
    forbid_reused_sentence_openers: bool = True


class ContinuityCfg(BaseModel):
    model_config = STRICT

    llm_judge: bool = True
    beat_coverage_min: float = Field(ge=0.0, le=1.0)


class ContextCfg(BaseModel):
    model_config = STRICT

    literal_tail_units: int = Field(ge=0)
    mid_summaries: bool = False
    rag_top_k: int = Field(ge=0)


class Profile(BaseModel):
    """Las tres familias de umbrales que aporta `config/profiles/<name>.yaml`."""

    model_config = STRICT

    name: str
    repetition: RepetitionCfg
    continuity: ContinuityCfg
    context: ContextCfg


class Config(BaseModel):
    model_config = STRICT

    project: ProjectCfg
    novel: NovelCfg
    profile: str
    llm: LLMCfg
    limits: LimitsCfg
    approval: ApprovalCfg
    repetition: RepetitionCfg
    continuity: ContinuityCfg
    context: ContextCfg

    def profile_settings(self) -> Profile:
        return Profile(
            name=self.profile,
            repetition=self.repetition,
            continuity=self.continuity,
            context=self.context,
        )

    def model_for(self, role: str) -> ModelCfg:
        resolved = ROLE_ALIASES.get(role, role)
        try:
            return self.llm.models[resolved]
        except KeyError:
            known = ", ".join(sorted(self.llm.models))
            raise ConfigError(
                f"no hay modelo configurado para el rol '{role}' en llm.models "
                f"(roles conocidos: {known})"
            ) from None


@dataclass(frozen=True)
class ConfigBundle:
    """Configuracion efectiva mas la trazabilidad de donde sale cada clave."""

    config: Config
    origins: dict[str, str]
    repo_root: Path
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Localizacion del repositorio
# --------------------------------------------------------------------------
def find_repo_root(start: Path | None = None) -> Path:
    """Localiza la raiz que contiene `config/default.yaml`."""
    env_home = os.environ.get("NOVELA_HOME")
    if env_home:
        candidate = Path(env_home).expanduser().resolve()
        if (candidate / "config" / "default.yaml").is_file():
            return candidate
        raise ConfigError(
            f"NOVELA_HOME apunta a '{candidate}', que no contiene config/default.yaml"
        )

    seeds = [start or Path.cwd(), Path(__file__).resolve().parent]
    for seed in seeds:
        for directory in [seed.resolve(), *seed.resolve().parents]:
            if (directory / "config" / "default.yaml").is_file():
                return directory
    raise ConfigError(
        "no se encuentra config/default.yaml: ejecuta la CLI dentro del repositorio "
        "o exporta NOVELA_HOME con su ruta"
    )


def project_dir(repo_root: Path, project_id: str) -> Path:
    return repo_root / "out" / project_id


# --------------------------------------------------------------------------
# Lectura y fusion
# --------------------------------------------------------------------------
def read_yaml(path: Path) -> JsonDict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"'{path}' debe contener un mapa YAML, no {type(data).__name__}")
    return data


def deep_merge(
    base: JsonDict, overlay: JsonDict, origins: dict[str, str], source: str, prefix: str = ""
) -> JsonDict:
    """Fusiona `overlay` sobre `base` clave a clave y anota el origen de cada hoja."""
    merged = dict(base)
    for key, value in overlay.items():
        path = f"{prefix}{key}"
        current = merged.get(key)
        if isinstance(value, dict):
            base_branch = current if isinstance(current, dict) else {}
            merged[key] = deep_merge(base_branch, value, origins, source, f"{path}.")
        else:
            merged[key] = value
            origins[path] = source
    return merged


def env_overrides(environ: dict[str, str] | None = None) -> JsonDict:
    """Traduce NOVELA__NOVEL__CHAPTERS=5 a {'novel': {'chapters': 5}}."""
    env = environ if environ is not None else dict(os.environ)
    overrides: JsonDict = {}
    for raw_key, raw_value in sorted(env.items()):
        if not raw_key.startswith(ENV_PREFIX):
            continue
        parts = [part.lower() for part in raw_key[len(ENV_PREFIX) :].split("__") if part]
        if not parts:
            continue
        assign(overrides, parts, yaml.safe_load(raw_value))
    return overrides


def assign(target: JsonDict, parts: list[str], value: Any) -> None:
    cursor = target
    for part in parts[:-1]:
        nxt = cursor.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[part] = nxt
        cursor = nxt
    cursor[parts[-1]] = value


def flag_overrides(flags: dict[str, Any]) -> JsonDict:
    """Traduce {'novel.chapters': 5} a la estructura anidada equivalente."""
    overrides: JsonDict = {}
    for dotted, value in flags.items():
        if value is None:
            continue
        assign(overrides, dotted.split("."), value)
    return overrides


# --------------------------------------------------------------------------
# Deteccion de claves desconocidas con sugerencia
# --------------------------------------------------------------------------
def model_for_annotation(annotation: Any) -> type[BaseModel] | None:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    if get_origin(annotation) in (Union, UnionType):
        for arg in get_args(annotation):
            found = model_for_annotation(arg)
            if found is not None:
                return found
    return None


def dict_value_model(annotation: Any) -> type[BaseModel] | None:
    if get_origin(annotation) is dict:
        args = get_args(annotation)
        if len(args) == 2:
            return model_for_annotation(args[1])
    return None


def check_unknown_keys(
    model_cls: type[BaseModel], data: JsonDict, origins: dict[str, str], prefix: str = ""
) -> None:
    """Falla de forma ruidosa ante una clave que el modelo no declara."""
    fields = model_cls.model_fields
    for key, value in data.items():
        path = f"{prefix}{key}"
        if key not in fields:
            source = origins.get(path, "la configuracion")
            suggestion = difflib.get_close_matches(key, list(fields), n=1, cutoff=0.5)
            hint = f" (¿querías decir '{prefix}{suggestion[0]}'?)" if suggestion else ""
            raise ConfigError(f"clave desconocida '{path}' en {source}{hint}")

        annotation = fields[key].annotation
        nested = model_for_annotation(annotation)
        if nested is not None and isinstance(value, dict):
            check_unknown_keys(nested, value, origins, f"{path}.")
            continue
        value_model = dict_value_model(annotation)
        if value_model is not None and isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict):
                    check_unknown_keys(value_model, sub_value, origins, f"{path}.{sub_key}.")


def translate_validation_error(error: ValidationError, origins: dict[str, str]) -> ConfigError:
    lines: list[str] = []
    for detail in error.errors():
        path = ".".join(str(part) for part in detail["loc"])
        source = origins.get(path, "la configuracion")
        lines.append(f"{path}: {detail['msg']} (definido en {source})")
    return ConfigError("configuracion invalida:\n  - " + "\n  - ".join(lines))


# --------------------------------------------------------------------------
# Coherencia cruzada
# --------------------------------------------------------------------------
def coherence_warnings(config: Config) -> list[str]:
    warnings: list[str] = []
    length = config.novel.length
    if length.unit == "lines" and length.target < 3:
        warnings.append(
            f"novel.length.target={length.target} líneas: un capítulo tan corto no puede "
            "sostener una estructura dramática (objetivo, conflicto, resultado)."
        )
    if length.unit == "words" and config.profile == "micro":
        warnings.append(
            "unit: words con profile: micro — los umbrales de repetición están desactivados "
            "y la detección de repetición no protegerá la obra. Usa profile: full."
        )
    if length.unit == "words" and length.tolerance == 0:
        warnings.append(
            "novel.length.tolerance=0 con unit: words exige una longitud exacta al vocablo, "
            "que ningún modelo alcanza de forma fiable. Usa 300-500."
        )
    return warnings


# --------------------------------------------------------------------------
# Resolucion
# --------------------------------------------------------------------------
def available_profiles(repo_root: Path) -> list[str]:
    directory = repo_root / "config" / "profiles"
    return sorted(path.stem for path in directory.glob("*.yaml"))


def _layer_sources(repo_root: Path, project_id: str | None) -> list[tuple[str, JsonDict]]:
    layers: list[tuple[str, JsonDict]] = [("novela.yaml", read_yaml(repo_root / "novela.yaml"))]
    if project_id:
        project_cfg = project_dir(repo_root, project_id) / "config.yaml"
        layers.append((str(Path("out") / project_id / "config.yaml"), read_yaml(project_cfg)))
    return layers


def resolve(
    *,
    repo_root: Path | None = None,
    project_id: str | None = None,
    flags: dict[str, Any] | None = None,
    environ: dict[str, str] | None = None,
) -> ConfigBundle:
    """Construye la configuracion efectiva. Se invoca en CADA comando: nunca se cachea."""
    root = repo_root or find_repo_root()
    origins: dict[str, str] = {}

    default_raw = read_yaml(root / "config" / "default.yaml")
    merged = deep_merge({}, default_raw, origins, "config/default.yaml")

    upper_layers = [
        *_layer_sources(root, project_id),
        ("variables de entorno NOVELA__*", env_overrides(environ)),
        ("flags de la CLI", flag_overrides(flags or {})),
    ]

    # Primera pasada: averiguar que perfil pide la capa mas prioritaria.
    probe = dict(merged)
    for source, layer in upper_layers:
        probe = deep_merge(probe, layer, {}, source)
    profile_name = str(probe.get("profile", merged.get("profile", "micro")))

    known = available_profiles(root)
    if profile_name not in known:
        raise ConfigError(
            f"perfil '{profile_name}' inexistente: no hay config/profiles/{profile_name}.yaml "
            f"(perfiles disponibles: {', '.join(known)})"
        )

    profile_raw = read_yaml(root / "config" / "profiles" / f"{profile_name}.yaml")
    merged = deep_merge(merged, profile_raw, origins, f"config/profiles/{profile_name}.yaml")
    for source, layer in upper_layers:
        merged = deep_merge(merged, layer, origins, source)

    check_unknown_keys(Config, merged, origins)
    try:
        config = Config.model_validate(merged)
    except ValidationError as error:
        raise translate_validation_error(error, origins) from error

    return ConfigBundle(
        config=config,
        origins=origins,
        repo_root=root,
        warnings=coherence_warnings(config),
    )


def get_dotted(config: Config, dotted: str) -> Any:
    cursor: Any = config
    for part in dotted.split("."):
        if isinstance(cursor, BaseModel):
            if part not in type(cursor).model_fields:
                raise ConfigError(f"clave desconocida '{dotted}': '{part}' no existe")
            cursor = getattr(cursor, part)
        elif isinstance(cursor, dict):
            if part not in cursor:
                raise ConfigError(f"clave desconocida '{dotted}': '{part}' no existe")
            cursor = cursor[part]
        else:
            raise ConfigError(f"clave desconocida '{dotted}': '{part}' no es navegable")
    return cursor


# --------------------------------------------------------------------------
# Escritura conservando comentarios
# --------------------------------------------------------------------------
KEY_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z0-9_.-]+)\s*:(?P<rest>.*)$")


def _split_comment(rest: str) -> tuple[str, str]:
    """Separa el valor del comentario final, respetando `#` dentro de comillas."""
    in_single = in_double = False
    for index, char in enumerate(rest):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return rest[:index].rstrip(), rest[index:]
    return rest.rstrip(), ""


def _find_key_line(lines: list[str], key: str, indent: int, start: int, end: int) -> int | None:
    for index in range(start, end):
        match = KEY_RE.match(lines[index])
        if match and match.group("key") == key and len(match.group("indent")) == indent:
            return index
    return None


def _block_end(lines: list[str], start: int, indent: int) -> int:
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        current = len(line) - len(line.lstrip())
        if current <= indent:
            return index
    return len(lines)


def set_yaml_value(path: Path, dotted: str, value: Any) -> None:
    """Escribe `dotted: value` en un YAML de usuario conservando sus comentarios."""
    rendered = yaml.safe_dump(value, default_flow_style=True, allow_unicode=True).strip()
    rendered = rendered.removesuffix("\n...").strip()

    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    parts = dotted.split(".")
    start, end, indent = 0, len(lines), 0

    for depth, part in enumerate(parts):
        found = _find_key_line(lines, part, indent, start, end)
        if found is None:
            block = [f"{' ' * indent}{p}:" for p in parts[depth:-1]]
            block.append(f"{' ' * (indent + 2 * (len(parts) - depth - 1))}{parts[-1]}: {rendered}")
            insert_at = end
            lines[insert_at:insert_at] = block
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
        if depth == len(parts) - 1:
            match = KEY_RE.match(lines[found])
            assert match is not None
            _, comment = _split_comment(match.group("rest"))
            suffix = f"  {comment}" if comment else ""
            lines[found] = f"{match.group('indent')}{part}: {rendered}{suffix}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
        start, end, indent = found + 1, _block_end(lines, found, indent), indent + 2

    raise ConfigError(f"no se ha podido escribir la clave '{dotted}' en {path}")
