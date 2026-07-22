"""
Descarga el histórico de la Quiniela de la Provincia de Buenos Aires - Ronda Nocturna
desde la fuente OFICIAL (Instituto Provincial de Lotería y Casinos) y arma un CSV
con los 20 números de cada sorteo, ordenado cronológicamente.

FUENTE OFICIAL (real, verificada por ingeniería inversa del sitio):
  https://loteria.gba.gob.ar/api-loteria/extractos/{AAAA-MM-DD}

  El sitio es una app Drupal: la URL estática "extractosOficiales/.../*.pdf"
  que se asumía originalmente NO EXISTE (devuelve 404 siempre). Los extractos
  reales se obtienen pidiendo esa API por fecha, que devuelve un JSON con un
  campo "html" conteniendo, para cada modalidad (La Previa, El Primero,
  Matutina, Vespertina, Nocturna), un PDF embebido como
  data:application/pdf;base64,.... Este script extrae solo la sección
  "Nocturna", decodifica el base64 y parsea el PDF resultante.

REQUISITOS (instalar antes de correr):
    pip install requests pdfplumber

CÓMO USAR:
    python descargar_quiniela_nocturna.py

  Por defecto descarga los últimos 365 días (hoy hacia atrás). Podés cambiar
  FECHA_INICIO y FECHA_FIN más abajo, o pasarlos como argumentos:

    python descargar_quiniela_nocturna.py 2025-06-01 2026-06-22

SALIDA:
    data/sorteos.csv (mismo archivo que usa el motor de predicción)
    Columnas: fecha,turno,loteria,posicion,numero,sorteo_nro
    Si el archivo ya existe, las filas nuevas se fusionan sin duplicar ni
    pisar lo que ya estaba (podés correr el script de nuevo más adelante
    para sumar días recientes).

NOTAS IMPORTANTES:
  - No hay sorteo los domingos (el script los salta automáticamente).
  - Cada request de la API devuelve ~5 MB de JSON (trae los PDFs de las 5
    modalidades juntos, aunque solo usemos Nocturna). Para 365 días son
    ~310 requests (excluyendo domingos) y varios cientos de MB descargados
    contra el servidor del Instituto. Calculá que el proceso puede tardar
    varios minutos y consumir banda ancha real - no lo corras a la ligera
    en rangos muy grandes sin necesidad.
  - Si para algún día no existe el extracto (feriado, sorteo suspendido,
    error de red), el script lo registra en un log y continúa sin detenerse.
  - Si el Instituto cambia el formato del PDF o de la API, el parsing puede
    fallar para esas fechas: revisá el archivo "errores.log" generado.
"""

import base64
import csv
import io
import re
import sys
import time
import logging
from datetime import date, timedelta
from pathlib import Path

import requests

try:
    import pdfplumber
except ImportError:
    print("Falta instalar pdfplumber. Corré: pip install pdfplumber")
    sys.exit(1)

# ----------------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------------

API_URL = "https://loteria.gba.gob.ar/api-loteria/extractos/{fecha}"

SECCION_NOCTURNA_RE = re.compile(
    r'<h3>\s*Nocturna.*?href="data:application/pdf;base64,([A-Za-z0-9+/=]+)"',
    re.IGNORECASE | re.DOTALL,
)

# Rango por defecto: últimos 365 días corridos hasta hoy.
FECHA_FIN_DEFAULT = date.today()
FECHA_INICIO_DEFAULT = FECHA_FIN_DEFAULT - timedelta(days=365)

CSV_SALIDA = "data/sorteos.csv"
LOG_ERRORES = "errores.log"

PAUSA_ENTRE_REQUESTS_SEG = 1.5  # subila si el servidor empieza a rechazar requests
TIMEOUT_SEG = 30  # cada respuesta pesa varios MB, un timeout corto corta de mas

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

logging.basicConfig(
    filename=LOG_ERRORES,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)


# ----------------------------------------------------------------------------
# PARSING DEL PDF
# ----------------------------------------------------------------------------

def extraer_datos_pdf(contenido_pdf: bytes, fecha: date):
    """
    Recibe los bytes de un PDF de extracto oficial ("Quiniela Múltiple") y
    devuelve una lista de tuplas (posicion, numero) para los 20 lugares del
    sorteo Nocturna - Provincia, junto con el número de sorteo.

    El PDF trae, en la misma página, Vespertina y Nocturna combinadas para
    6 jurisdicciones (Provincia, Ciudad, Cordoba, Santa Fe, Entre Rios,
    Montevideo), cada una en su propia tabla de pdfplumber con esta forma:

        [['NOCTURNA', None, ...],
         ['<nro sorteo>', None, ...],
         ['Realizado a las 21:00', None, ...],
         ['PROVINCIA', None, ...],
         ['1º\\nPremio', None, None, '<primer digito>', None, '<resto>', None],
         ['1', '', '<numero pos 1>', None, '11', '', '<numero pos 11>'],
         ...
         ['10', '', '<numero pos 10>', None, '20', '', '<numero pos 20>']]

    Se busca puntualmente la tabla NOCTURNA + PROVINCIA (evita mezclar con
    las otras jurisdicciones, que vienen en tablas separadas en el mismo PDF).
    """
    tabla_objetivo = None
    with pdfplumber.open(io.BytesIO(contenido_pdf)) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                if not tabla or len(tabla) < 15:
                    continue
                encabezado = (tabla[0][0] or "").strip().upper()
                jurisdiccion = (tabla[3][0] or "").strip().upper()
                if encabezado == "NOCTURNA" and jurisdiccion == "PROVINCIA":
                    tabla_objetivo = tabla
                    break
            if tabla_objetivo:
                break

    if tabla_objetivo is None:
        raise ValueError("No se encontró la tabla 'NOCTURNA' / 'PROVINCIA' en el PDF")

    sorteo_nro = (tabla_objetivo[1][0] or "").strip()

    # El ancho de columnas detectado por pdfplumber varía según el día (a veces
    # hay una columna vacía extra, a veces no). En vez de indexar por posición
    # fija, se descartan celdas vacías: siempre quedan 4 valores por fila
    # (posicion_izq, numero_izq, posicion_der, numero_der).
    resultados = []
    for fila in tabla_objetivo[5:15]:
        celdas = [c.strip() for c in fila if c and c.strip()]
        if len(celdas) != 4:
            raise ValueError(f"Fila de tabla con formato inesperado: {fila}")
        pos_izq, num_izq, pos_der, num_der = celdas
        resultados.append((int(pos_izq), num_izq))
        resultados.append((int(pos_der), num_der))

    resultados.sort(key=lambda x: x[0])
    return resultados, sorteo_nro


# ----------------------------------------------------------------------------
# DESCARGA
# ----------------------------------------------------------------------------

def descargar_un_dia(fecha: date):
    """Descarga y parsea el extracto de un día. Devuelve lista de filas para el CSV."""
    if fecha.weekday() == 6:  # domingo = 6 (lunes=0)
        return []  # no hay sorteo

    url = API_URL.format(fecha=fecha.isoformat())

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SEG)
    except requests.RequestException as e:
        logging.info(f"{fecha.isoformat()} - ERROR DE CONEXION - {e} - url={url}")
        return []

    if resp.status_code != 200:
        logging.info(f"{fecha.isoformat()} - HTTP {resp.status_code} - url={url}")
        return []

    try:
        html = resp.json().get("html", "")
    except ValueError as e:
        logging.info(f"{fecha.isoformat()} - Respuesta no es JSON valido - {e} - url={url}")
        return []

    match = SECCION_NOCTURNA_RE.search(html)
    if not match:
        logging.info(f"{fecha.isoformat()} - No se encontro seccion 'Nocturna' en la respuesta - url={url}")
        return []

    try:
        pdf_bytes = base64.b64decode(match.group(1))
    except Exception as e:
        logging.info(f"{fecha.isoformat()} - ERROR AL DECODIFICAR BASE64 - {e} - url={url}")
        return []

    try:
        posiciones, sorteo_nro = extraer_datos_pdf(pdf_bytes, fecha)
    except Exception as e:
        logging.info(f"{fecha.isoformat()} - ERROR AL PARSEAR PDF - {e} - url={url}")
        return []

    if len(posiciones) < 20:
        logging.info(
            f"{fecha.isoformat()} - Solo se extrajeron {len(posiciones)}/20 posiciones - url={url}"
        )

    filas = []
    for pos, numero in posiciones:
        filas.append({
            "fecha": fecha.isoformat(),
            "turno": "Nocturna",
            "loteria": "Provincia",
            "posicion": pos,
            "numero": numero,
            "sorteo_nro": sorteo_nro,
        })
    return filas


def main():
    if len(sys.argv) == 3:
        fecha_inicio = date.fromisoformat(sys.argv[1])
        fecha_fin = date.fromisoformat(sys.argv[2])
    else:
        fecha_inicio = FECHA_INICIO_DEFAULT
        fecha_fin = FECHA_FIN_DEFAULT

    print(f"Descargando Quiniela Provincia - Nocturna")
    print(f"Desde: {fecha_inicio.isoformat()}  Hasta: {fecha_fin.isoformat()}")
    print(f"Esto puede tardar varios minutos. Revisá '{LOG_ERRORES}' si faltan días.\n")

    todas_las_filas = []
    dia_actual = fecha_inicio
    total_dias = (fecha_fin - fecha_inicio).days + 1
    contador = 0

    while dia_actual <= fecha_fin:
        contador += 1
        print(f"[{contador}/{total_dias}] {dia_actual.isoformat()}...", end=" ")

        filas = descargar_un_dia(dia_actual)
        if filas:
            todas_las_filas.extend(filas)
            print(f"OK ({len(filas)} números)")
        else:
            print("sin datos (ver log)")

        dia_actual += timedelta(days=1)
        time.sleep(PAUSA_ENTRE_REQUESTS_SEG)

    # Si ya existe un CSV previo (de una corrida anterior con otro rango de
    # fechas), se fusiona en vez de pisarlo, evitando duplicados.
    existentes = []
    salida_path = Path(CSV_SALIDA)
    if salida_path.exists():
        with open(salida_path, newline="", encoding="utf-8") as f:
            existentes = list(csv.DictReader(f))

    vistos = set()
    combinadas = []
    for fila in existentes + todas_las_filas:
        clave = (fila["fecha"], fila.get("turno", "Nocturna"), fila.get("loteria", "Provincia"), str(fila["posicion"]))
        if clave in vistos:
            continue
        vistos.add(clave)
        combinadas.append(fila)

    combinadas.sort(key=lambda f: (f["fecha"], int(f["posicion"])))

    salida_path.parent.mkdir(parents=True, exist_ok=True)
    with open(salida_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fecha", "turno", "loteria", "posicion", "numero", "sorteo_nro"])
        writer.writeheader()
        writer.writerows(combinadas)

    print(f"\nListo. {len(todas_las_filas)} filas nuevas. Total en '{CSV_SALIDA}': {len(combinadas)} filas.")
    print(f"Revisá '{LOG_ERRORES}' para ver qué días no se pudieron descargar.")


if __name__ == "__main__":
    main()
