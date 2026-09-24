"""Operaciones del contrato que todavía no están implementadas.

Cada paso que implementa un endpoint lo saca de aquí. El P49 exige que quede vacía
(`specs/plan1.md` § 4.2).
"""

PENDIENTES: frozenset[str] = frozenset(
    {
        "validarBrief",
        "listarVersiones",
        "obtenerVersion",
        "listarCapitulos",
        "obtenerCapitulo",
        "obtenerFicha",
        "obtenerPortada",
        "listarHechos",
        "crearSolicitudCambio",
        "obtenerSolicitudCambio",
        "confirmarSolicitudCambio",
        "exportarVersion",
        "descargarExport",
    }
)
