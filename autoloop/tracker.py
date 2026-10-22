#!/usr/bin/env python3
"""Lee REQUIREMENTS.md y el estado del loop para decidir qué hacer.

Subcomandos:
  next      -> elige la próxima tarea ejecutable (JSON por stdout)
  check     -> control de finalización (JSON por stdout)
  report    -> escribe el informe de bloqueos/estado en Markdown
  render    -> actualiza el bloque autogenerado de PROJECT_STATUS.md
  attempt   -> suma/resetea intentos fallidos de una tarea

Códigos de salida de `next` y `check`:
  0  = todos los requisitos obligatorios están probados (proyecto terminado)
  10 = hay al menos una tarea ejecutable
  20 = quedan requisitos pero ninguno es ejecutable (bloqueados / sin intentos)
  2  = REQUIREMENTS.md ausente o con formato inválido

Solo usa la biblioteca estándar para poder correr en cualquier entorno.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ESTADOS = {"pendiente", "en_progreso", "implementado", "probado", "bloqueado"}
COLUMNAS = ["id", "prioridad", "obligatorio", "estado", "depende", "prueba", "descripcion"]
MAX_INTENTOS_DEFAULT = 3

EXIT_COMPLETO, EXIT_TRABAJO, EXIT_BLOQUEADO, EXIT_FORMATO = 0, 10, 20, 2

MARCA_INICIO = "<!-- autoloop:inicio -->"
MARCA_FIN = "<!-- autoloop:fin -->"


class FormatoInvalido(Exception):
    pass


def _norm(texto: str) -> str:
    return texto.strip().strip("`").strip()


def leer_requisitos(path: Path) -> list[dict]:
    """Parsea la tabla de requisitos. Una fila por requisito:

    | ID | Prioridad | Obligatorio | Estado | Depende de | Prueba | Descripción |
    """
    if not path.exists():
        raise FormatoInvalido(f"No existe {path}")
    filas: list[dict] = []
    vistos: set[str] = set()
    for n, linea in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.lstrip().startswith("|"):
            continue
        celdas = [_norm(c) for c in linea.strip().strip("|").split("|")]
        if not celdas or celdas[0].lower() in ("id", "") or set(celdas[0]) <= set("-: "):
            continue
        if len(celdas) < len(COLUMNAS):
            raise FormatoInvalido(f"Línea {n}: se esperaban {len(COLUMNAS)} columnas")
        fila = dict(zip(COLUMNAS, celdas[: len(COLUMNAS)]))
        fila["estado"] = fila["estado"].lower()
        if fila["estado"] not in ESTADOS:
            raise FormatoInvalido(f"Línea {n}: estado desconocido '{fila['estado']}'")
        if not re.fullmatch(r"P[0-3]", fila["prioridad"]):
            raise FormatoInvalido(f"Línea {n}: prioridad debe ser P0..P3")
        if fila["id"] in vistos:
            raise FormatoInvalido(f"Línea {n}: ID duplicado {fila['id']}")
        vistos.add(fila["id"])
        fila["obligatorio"] = fila["obligatorio"].lower() in ("sí", "si", "yes", "true", "x")
        fila["depende"] = [d.strip() for d in re.split(r"[,\s]+", fila["depende"]) if d.strip() not in ("", "-")]
        fila["linea"] = n
        filas.append(fila)
    if not filas:
        raise FormatoInvalido(f"{path} no tiene filas de requisitos")
    return filas


def esta_hecho(req: dict) -> bool:
    """'Probado' solo cuenta si la columna Prueba indica cómo se verificó."""
    return req["estado"] == "probado" and req["prueba"] not in ("", "-")


def leer_intentos(path: Path) -> dict[str, int]:
    try:
        return {k: int(v) for k, v in json.loads(path.read_text(encoding="utf-8")).items()}
    except (FileNotFoundError, ValueError):
        return {}


def analizar(reqs: list[dict], intentos: dict[str, int], max_intentos: int) -> dict:
    por_id = {r["id"]: r for r in reqs}
    obligatorios = [r for r in reqs if r["obligatorio"]]
    faltan = [r for r in obligatorios if not esta_hecho(r)]

    ejecutables, no_ejecutables = [], []
    for r in reqs:
        if esta_hecho(r):
            continue
        motivo = None
        if r["estado"] == "bloqueado":
            motivo = "estado bloqueado (ver BLOCKERS.md)"
        elif intentos.get(r["id"], 0) >= max_intentos:
            motivo = f"{intentos[r['id']]} intentos fallidos (límite {max_intentos})"
        else:
            pendientes = [d for d in r["depende"] if d not in por_id or not esta_hecho(por_id[d])]
            if pendientes:
                motivo = "depende de " + ", ".join(pendientes)
        (no_ejecutables if motivo else ejecutables).append({**r, "motivo": motivo})

    # Primero lo obligatorio, luego prioridad, luego lo ya empezado, luego orden del archivo.
    ejecutables.sort(key=lambda r: (not r["obligatorio"], r["prioridad"],
                                    r["estado"] not in ("en_progreso", "implementado"), r["linea"]))
    if not faltan:
        codigo = EXIT_COMPLETO
    elif ejecutables:
        codigo = EXIT_TRABAJO
    else:
        codigo = EXIT_BLOQUEADO
    # Si lo obligatorio está todo probado igual se pueden hacer opcionales,
    # pero el proyecto ya se considera terminado (código 0).
    return {
        "codigo": codigo,
        "completo": not faltan,
        "total": len(reqs),
        "obligatorios": len(obligatorios),
        "obligatorios_probados": len(obligatorios) - len(faltan),
        "obligatorios_faltantes": [r["id"] for r in faltan],
        "siguiente": _publico(ejecutables[0]) if ejecutables else None,
        "ejecutables": [r["id"] for r in ejecutables],
        "no_ejecutables": [{"id": r["id"], "motivo": r["motivo"], "obligatorio": r["obligatorio"]}
                           for r in no_ejecutables],
    }


def _publico(r: dict) -> dict:
    return {k: r[k] for k in ("id", "prioridad", "obligatorio", "estado", "depende", "prueba", "descripcion")}


def informe_md(res: dict, iteraciones: list[dict]) -> str:
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [f"# Informe del loop autónomo — {ahora}", ""]
    if res["completo"]:
        out.append("**Estado: TERMINADO.** Todos los requisitos obligatorios están probados.")
    elif res["codigo"] == EXIT_BLOQUEADO:
        out.append("**Estado: DETENIDO POR BLOQUEOS.** Quedan requisitos obligatorios y ninguno es ejecutable sin intervención.")
    else:
        out.append(f"**Estado: EN CURSO.** Próxima tarea: `{res['siguiente']['id']}`.")
    out += ["", f"- Obligatorios probados: {res['obligatorios_probados']}/{res['obligatorios']}",
            f"- Obligatorios faltantes: {', '.join(res['obligatorios_faltantes']) or 'ninguno'}",
            f"- Ejecutables ahora: {', '.join(res['ejecutables']) or 'ninguno'}", ""]
    if res["no_ejecutables"]:
        out += ["## Intervenciones necesarias", "", "| Requisito | Obligatorio | Motivo |", "|---|---|---|"]
        out += [f"| {b['id']} | {'Sí' if b['obligatorio'] else 'No'} | {b['motivo']} |" for b in res["no_ejecutables"]]
        out += ["", "Detalle de cada bloqueo y la acción requerida: `BLOCKERS.md`.", ""]
    if iteraciones:
        costo = sum(float(i.get("costo_usd") or 0) for i in iteraciones)
        out += ["## Últimas iteraciones", "", f"Costo estimado acumulado: US$ {costo:.2f}", "",
                "| # | Fecha | Tarea | Resultado | Costo US$ |", "|---|---|---|---|---|"]
        for i in iteraciones[-10:]:
            out.append(f"| {i.get('iteracion')} | {i.get('inicio', '')[:16]} | {i.get('tarea')} | "
                       f"{i.get('resultado')} | {float(i.get('costo_usd') or 0):.2f} |")
    return "\n".join(out) + "\n"


def leer_iteraciones(path: Path) -> list[dict]:
    if not path.exists():
        return []
    filas = []
    for linea in path.read_text(encoding="utf-8").splitlines():
        try:
            filas.append(json.loads(linea))
        except ValueError:
            continue  # una línea truncada por un corte no debe romper la reanudación
    return filas


def render_status(status_path: Path, bloque: str) -> None:
    texto = status_path.read_text(encoding="utf-8") if status_path.exists() else "# PROJECT_STATUS\n"
    nuevo = f"{MARCA_INICIO}\n{bloque.rstrip()}\n{MARCA_FIN}"
    if MARCA_INICIO in texto and MARCA_FIN in texto:
        antes, resto = texto.split(MARCA_INICIO, 1)
        _, despues = resto.split(MARCA_FIN, 1)
        texto = antes + nuevo + despues
    else:
        texto = texto.rstrip() + "\n\n" + nuevo + "\n"
    status_path.write_text(texto, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("comando", choices=["next", "check", "report", "render", "attempt"])
    p.add_argument("--root", default=".", help="raíz del proyecto")
    p.add_argument("--max-intentos", type=int, default=MAX_INTENTOS_DEFAULT)
    p.add_argument("--out", help="report: archivo de salida")
    p.add_argument("--tarea", help="attempt: ID de la tarea")
    p.add_argument("--reset", action="store_true", help="attempt: poner el contador en 0")
    a = p.parse_args(argv)

    root = Path(a.root)
    estado_dir = root / "autoloop" / "state"
    intentos_path = estado_dir / "attempts.json"

    if a.comando == "attempt":
        if not a.tarea:
            p.error("attempt requiere --tarea")
        intentos = leer_intentos(intentos_path)
        intentos[a.tarea] = 0 if a.reset else intentos.get(a.tarea, 0) + 1
        estado_dir.mkdir(parents=True, exist_ok=True)
        intentos_path.write_text(json.dumps(intentos, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(intentos[a.tarea])
        return 0

    try:
        reqs = leer_requisitos(root / "REQUIREMENTS.md")
    except FormatoInvalido as e:
        print(json.dumps({"codigo": EXIT_FORMATO, "error": str(e)}, ensure_ascii=False))
        return EXIT_FORMATO
    res = analizar(reqs, leer_intentos(intentos_path), a.max_intentos)

    if a.comando in ("next", "check"):
        print(json.dumps(res, ensure_ascii=False))
        return res["codigo"]
    iteraciones = leer_iteraciones(estado_dir / "iterations.jsonl")
    md = informe_md(res, iteraciones)
    if a.comando == "report":
        if a.out:
            Path(a.out).write_text(md, encoding="utf-8")
        print(md, end="")
        return 0
    # render: solo la parte de resumen, sin el título con fecha (evita diffs ruidosos)
    render_status(root / "PROJECT_STATUS.md", "\n".join(md.splitlines()[2:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
