"""Actualiza data/sorteos.csv con los días nuevos desde la última corrida y
después genera: (1) el reporte rápido diario + grillas visuales (run.py) y
(2) la investigación científica completa (investigacion_cientifica.py, Fases
2 a 6 y 8: batería de aleatoriedad, análisis de generador, ML condicional,
Monte Carlo/bootstrap y reporte científico en Markdown+PDF). Es lo que
ejecuta ejecutar.bat / el acceso directo del escritorio.

Uso:
    python actualizar_y_predecir.py [argumentos, ej: --top 15]
"""
from __future__ import annotations

import csv
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

CSV_PATH = Path("data/sorteos.csv")
DIAS_BOOTSTRAP = 30  # si no hay CSV todavia, cuantos dias hacia atras arrancar


def ultima_fecha_en_csv() -> date | None:
    if not CSV_PATH.exists():
        return None
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        return None
    return max(date.fromisoformat(fila["fecha"]) for fila in filas)


def main() -> None:
    hoy = date.today()
    ultima = ultima_fecha_en_csv()
    fecha_inicio = (ultima + timedelta(days=1)) if ultima else (hoy - timedelta(days=DIAS_BOOTSTRAP))

    if fecha_inicio <= hoy:
        print(f"Actualizando datos: {fecha_inicio.isoformat()} -> {hoy.isoformat()}...")
        resultado = subprocess.run(
            [sys.executable, "descargar_quiniela_nocturna.py", fecha_inicio.isoformat(), hoy.isoformat()]
        )
        if resultado.returncode != 0:
            print("AVISO: la actualización de datos terminó con errores, se sigue con lo que ya había.")
    else:
        print("Los datos ya están al día.")

    print("\nGenerando reporte rápido + grillas visuales...")
    subprocess.run([sys.executable, "run.py", "--csv", str(CSV_PATH), *sys.argv[1:]], check=True)

    print("\nCorriendo investigación científica completa (puede tardar unos segundos)...")
    subprocess.run(
        [sys.executable, "investigacion_cientifica.py", "--csv", str(CSV_PATH), *sys.argv[1:]], check=True
    )


if __name__ == "__main__":
    main()
