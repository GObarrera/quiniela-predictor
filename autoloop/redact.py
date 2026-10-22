#!/usr/bin/env python3
"""Filtro stdin -> stdout que oculta claves y datos personales antes de guardar logs."""
import re
import sys

PATRONES = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"), "[CLAVE-OCULTA]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"), "[TOKEN-OCULTO]"),
    (re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"), "[CLAVE-OCULTA]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "[TOKEN-OCULTO]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{12,}"), "Bearer [TOKEN-OCULTO]"),
    (re.compile(r"(?i)\b([A-Z0-9_]*(?:api[_-]?key|secret|token|password|passwd|contrase(?:ñ|n)a)[A-Z0-9_]*)"
                r"(\s*[:=]\s*)(['\"]?)[^\s'\",]{4,}\3"), r"\1\2\3[OCULTO]\3"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[CLAVE-PRIVADA-OCULTA]"),
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[EMAIL-OCULTO]"),
    # Teléfonos en formato internacional (+54 9 11 1234-5678). Exige '+' para no tocar fechas ni cifras.
    (re.compile(r"\+\d{1,3}[\s-]?(?:\d[\s-]?){8,12}\d"), "[TELEFONO-OCULTO]"),
]


def redactar(texto: str) -> str:
    for patron, reemplazo in PATRONES:
        texto = patron.sub(reemplazo, texto)
    return texto


if __name__ == "__main__":
    sys.stdout.write(redactar(sys.stdin.read()))
