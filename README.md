# Motor de análisis — Quiniela Plus

Herramienta local de estadística descriptiva sobre resultados históricos de
Quiniela Plus. **No predice números ganadores con certeza.** Calcula
frecuencias, ausencias y una prueba de aleatoriedad (chi-cuadrado), y arma
un ranking heurístico que solo tiene sentido si esa prueba muestra alguna
desviación real de la uniformidad — lo cual el reporte deja explícito cada vez.

## Requisitos

- Python 3.10 o superior instalado (en esta PC se usa vía el lanzador `py`).
- Conexión a internet: para instalar dependencias la primera vez, y cada vez
  que se actualizan los datos (descarga del sitio oficial).

## Dónde quedan los reportes

Todos los reportes (rápido, grillas, científico) se guardan directo en
`C:\Users\gabri\OneDrive\QuinielaReportes` en vez de en una carpeta local del
proyecto. Como esa carpeta ya está sincronizada con OneDrive, cualquier
reporte nuevo queda accesible desde el celular (app de OneDrive) sin
necesidad de prender esta PC — eso sí, la PC tiene que estar prendida y
correr el acceso directo para que se **genere** un reporte nuevo; esto no es
un servicio en la nube, solo sincroniza lo que ya se generó localmente.
Se puede cambiar con `--reports-dir <carpeta>` en cualquiera de los scripts.

## Esquema del CSV (`data/sorteos.csv`)

| Columna    | Obligatoria | Descripción                                      | Ejemplo     |
|------------|-------------|---------------------------------------------------|-------------|
| fecha      | Sí          | Fecha del sorteo (YYYY-MM-DD)                     | 2026-01-05  |
| numero     | Sí          | Número extraído (se conservan ceros a la izquierda)| 0912        |
| turno      | No          | Tanda del sorteo (Matutina/Vespertina/Nocturna)    | Nocturna    |
| loteria    | No          | Nombre de la lotería/jurisdicción                  | Nacional    |
| posicion   | No          | Posición del premio dentro del extracto            | 1           |

Una fila por número extraído. Este archivo ya viene poblado con el
histórico real de Quiniela Nocturna - Provincia descargado del sitio
oficial (ver más abajo); no hace falta tocarlo a mano.

## Cómo correrlo

Doble clic en `ejecutar.bat`. Cada vez que lo corrés:

1. **Actualiza los datos primero**: descarga automáticamente del sitio
   oficial (`loteria.gba.gob.ar`) todos los días que falten desde la última
   vez que corriste esto hasta hoy, y los suma a `data/sorteos.csv` sin
   duplicar. Si el sorteo Nocturna de hoy todavía no salió (es a las 21:00),
   simplemente no encuentra nada para hoy y sigue sin problema — la próxima
   vez que lo corras después de esa hora, lo trae.
2. **Genera el reporte** con los datos ya actualizados.
3. Imprime el reporte en la consola y guarda una copia con fecha/hora en
   `reports/reporte_YYYYMMDD_HHMMSS.md`.
4. **Abre automáticamente en el navegador** una página con tres grillas
   separadas de terminaciones (últimos 2 dígitos, 00 a 99) — Calientes,
   Frías y Predicción — cada una mostrando solo los números de esa
   categoría (`reports/grilla_terminaciones.html`, se sobrescribe cada vez).
   Desactivable con `ejecutar.bat --sin-grilla`.
5. **Corre la investigación científica completa** (Fases 2 a 6 y 8 del
   protocolo original) y abre el PDF resultante. Ver sección siguiente.
   Desactivable con `ejecutar.bat --sin-abrir` (no abre el PDF, pero igual
   lo genera).

La primera vez además crea el entorno virtual e instala dependencias
(pandas, scipy, requests, pdfplumber, scikit-learn, fpdf2); las siguientes
veces corre directo.

Para pasar parámetros al doble-clic:

```
ejecutar.bat --top 15 --n-resamples 1000000
```

O manualmente sin el .bat:

```
.venv\Scripts\python.exe actualizar_y_predecir.py --top 15
```

Parámetros disponibles (algunos aplican solo a uno de los dos reportes,
las flags no reconocidas por cada script se ignoran automáticamente):
`--top` (cuántos números mostrar / k del backtest), `--ventana` (sorteos
recientes para la frecuencia móvil, solo run.py), `--digitos`/`--max-numero`
(formato del número, solo run.py), `--alpha` (significancia, ambos),
`--n-resamples` (remuestreos bootstrap de la Fase 6, default 100.000, solo
investigacion_cientifica.py), `--sin-grilla` (run.py), `--sin-abrir`
(investigacion_cientifica.py).

## Qué hace el reporte rápido diario (run.py), en criollo

1. **Frecuencia histórica y reciente** de cada número (0 a max-numero).
2. **Ausencia actual**: hace cuántos sorteos no sale cada número.
3. **Chi-cuadrado de uniformidad**: contrasta si la distribución observada
   es compatible con azar puro. Si el p-valor no es significativo, el
   reporte lo dice explícitamente y aclara que el ranking siguiente es
   solo descriptivo.
4. **Ranking heurístico**: combina los tres puntos anteriores en un score.
   Es una curiosidad estadística, no una garantía — dos apuestas seguidas
   nunca están garantizadas por historial pasado en un sorteo real.

## Qué hace la investigación científica completa (investigacion_cientifica.py)

Implementa las Fases 2 a 6 y 8 del protocolo original de investigación
(se excluyeron a propósito el dashboard web y el empaquetado Docker/CI-CD,
pensados para un equipo/servidor, no para un script personal). Trabaja
sobre las **terminaciones** (00-99), no el número completo: con ~6000
sorteos, una tabla de 10000x10000 sería demasiado dispersa para que los
tests de dependencia y los modelos de ML sean válidos.

- **Fase 2 extendida**: pares/impares, altos/bajos, correlación entre las
  20 posiciones del extracto, autocorrelación, correlación cruzada.
- **Fase 3 completa**: Chi-cuadrado, Kolmogorov-Smirnov, Anderson-Darling,
  test de rachas (Wald-Wolfowitz), entropía de Shannon y condicional, test
  de independencia — cada uno con estadístico, p-valor (o valor crítico
  tabulado) e interpretación explícita. Se aplica **corrección de
  Benjamini-Hochberg** por comparaciones múltiples antes de decidir si algo
  es realmente significativo (correr 5 tests a la vez sin corregir da
  ~23% de chance de al menos un falso positivo).
- **Fase 4 (exploratoria)**: espectro de Fourier y detección de ciclos por
  autocorrelación, más un score bayesiano heurístico (no una prueba) de
  "probabilidad de generador reproducible", con intervalo de credibilidad y
  advertencia si la muestra es chica. No se simulan generadores concretos
  (LCG, Mersenne Twister, etc.): eso requeriría asumir semilla/parámetros,
  algo que el protocolo pide evitar explícitamente.
- **Fase 5 (condicional)**: cadena de Markov de orden 1, y un RandomForest
  como "detector de señal" contra un baseline aleatorio (accuracy, log-loss,
  Brier), con validación cruzada temporal. **Solo se entrena si la Fase 3
  mostró más de un test significativo tras la corrección** — si no, el
  reporte lo documenta como omitido en vez de forzar un resultado.
- **Fase 6**: backtesting walk-forward (el ranking en cada sorteo se
  calcula solo con datos previos, nunca mirando el futuro) + bootstrap
  (100.000 remuestreos por defecto) para el intervalo de confianza de la
  diferencia de tasas de acierto contra el azar.
- **Fase 8**: todo lo anterior se combina en `reports/reporte_cientifico.md`
  y `.pdf`, respondiendo explícitamente las 5 preguntas del protocolo con
  sus métricas y p-valores.

Con el año de histórico real cargado hasta ahora, la conclusión es
consistente en todos los frentes: el sorteo se comporta como un proceso
aleatorio, y ningún ranking o modelo evaluado supera al azar de forma
robusta.

## Estructura del proyecto

```
quiniela-predictor/
  data/sorteos.csv               <- histórico real, se actualiza solo
  errores.log                    <- días que no se pudieron descargar y por qué
  src/
    config.py                     <- ruta de OneDrive donde se guardan los reportes
    loader.py                    <- lectura y validación del CSV
    stats.py                     <- frecuencias, frecuencia móvil, ausencias
    distribuciones.py             <- decenas, paridad, altos/bajos, modular
    dependencias.py               <- correlación entre posiciones, ACF, cruzada
    randomness.py                 <- batería completa de tests de aleatoriedad
    generador.py                  <- espectro Fourier, ciclos, score bayesiano
    modelos_ml.py                  <- gate + RandomForest vs baseline + Markov
    montecarlo.py                  <- backtesting walk-forward + bootstrap
    predictor.py                  <- score heurístico combinado (run.py)
    report.py                     <- arma el reporte rápido de texto
    reporte_cientifico.py          <- arma el reporte científico (MD + PDF)
    grid_html.py                   <- arma las grillas visuales HTML
    terminaciones.py               <- deriva últimos 2 dígitos para reusar stats
  run.py                          <- reporte rápido diario + grillas (CLI)
  investigacion_cientifica.py    <- investigación completa Fases 2-6+8 (CLI)
  descargar_quiniela_nocturna.py <- solo la descarga (CLI)
  actualizar_y_predecir.py       <- descarga + ambos reportes (lo que corre el .bat)
  ejecutar.bat                   <- doble clic: corre actualizar_y_predecir.py
  requirements.txt
```

## Fuente de los datos

`descargar_quiniela_nocturna.py` descarga de
`https://loteria.gba.gob.ar/api-loteria/extractos/{fecha}` (API real del
sitio del Instituto Provincial de Lotería y Casinos, encontrada por
ingeniería inversa del sitio — la URL de PDF estático que se asumía al
principio no existe). De la respuesta se toma solo la sección "Nocturna" /
"Provincia" (hay más jurisdicciones y modalidades en el mismo extracto,
se ignoran) y se parsean sus 20 posiciones. Cada request pesa varios MB,
así que actualizaciones día a día son baratas pero un backfill de meses
tarda minutos — normal, no es un error.
