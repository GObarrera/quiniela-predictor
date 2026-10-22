# Loop autónomo de desarrollo (`autoloop/`)

Ejecuta Claude Code en modo no interactivo (`claude -p`) en iteraciones **limitadas**. Cada
iteración toma la tarea ejecutable de mayor prioridad de `REQUIREMENTS.md`, la implementa, la
verifica de forma independiente y registra el resultado. Ninguna invocación depende de la memoria
de la anterior: **el estado vive en los archivos del repositorio**.

## Entorno detectado y elección

| | |
|---|---|
| Sistema donde se desarrolló y probó | Linux x86_64 (contenedor), bash, Python 3.13, git, `flock`, `timeout` |
| Claude Code | 2.1.307, con `-p`, `--output-format json`, `--max-budget-usd`, `--allowedTools`, `--permission-mode` |
| PowerShell | no disponible en el entorno → no se pudo probar un `.ps1`, así que no se entrega uno |
| Implementación | **Bash + Python (solo biblioteca estándar)** |

En Windows (la PC donde corre `ejecutar.bat`) usalo desde **WSL** (recomendado) o **Git Bash**.
En Git Bash no hay `flock`: el script usa automáticamente un lock por directorio con detección de
proceso muerto. Si Python se llama `py`, exportá `PYTHON=py`.

## Instalación

1. Instalar Claude Code y autenticarse una vez de forma interactiva (`claude`, luego `/login`), o
   exportar `ANTHROPIC_API_KEY` en la sesión. **Nunca** pongas la clave en `config.env` ni en el repo.
2. Python 3.10+ y git en el `PATH`.
3. Desde la raíz del repo: `chmod +x autoloop/*.sh autoloop/tests/*.sh`
4. Verificar: `autoloop/autoloop.sh test` (38 pruebas, sin Claude ni red, ~30 s).

## Archivos

| Archivo | Rol |
|---|---|
| `REQUIREMENTS.md` | Tabla de requisitos: prioridad, obligatorio, estado, dependencias, prueba. Fuente de verdad. |
| `PROJECT_STATUS.md` | Resumen humano + bloque autogenerado (`autoloop:inicio/fin`). |
| `ROADMAP.md` / `BLOCKERS.md` | Plan y bloqueos que requieren intervención. |
| `autoloop/autoloop.sh` | El loop. |
| `autoloop/tracker.py` | Selección de tarea, control de finalización, informe, contador de intentos. |
| `autoloop/config.env` | Límites, pausas, presupuesto, permisos. Todo se puede sobreescribir por variable de entorno. |
| `autoloop/prompt.md` | Instrucciones que recibe Claude en cada iteración. |
| `autoloop/redact.py` | Oculta claves, tokens, emails y teléfonos antes de escribir cualquier registro. |
| `autoloop/state/iterations.jsonl` | Historial estructurado (versionado). |
| `autoloop/state/attempts.json` | Intentos fallidos por tarea (versionado). |
| `autoloop/PRUEBA_REAL.md` | Informe de la ejecución de prueba real con Claude. |
| `autoloop/INFORME.md` | Informe de estado/bloqueos al cierre de cada corrida (versionado). |
| `autoloop/logs/` | Salida cruda redactada de cada iteración, prompts y pruebas (no versionado). |

## Uso

```bash
autoloop/autoloop.sh start --dry-run                 # muestra la próxima tarea y el comando; no hace nada
autoloop/autoloop.sh start --mock                    # loop completo con un doble de Claude: sin red, sin costo
autoloop/autoloop.sh start --test-mode --max-iterations 2   # Claude real, sin comunicaciones externas
autoloop/autoloop.sh start                           # ejecución habitual (límites de config.env)
autoloop/autoloop.sh status                          # estado del proceso y del proyecto
autoloop/autoloop.sh stop                            # se detiene al terminar la iteración en curso
autoloop/autoloop.sh stop --now                      # corta también la invocación en curso
autoloop/autoloop.sh resume                          # borra el pedido de STOP y continúa
autoloop/autoloop.sh report                          # escribe autoloop/INFORME.md
```

**Comando habitual recomendado:**

```bash
autoloop/autoloop.sh start --test-mode
```

(`--test-mode` mientras no haya credenciales aprobadas para email/WhatsApp; quitarlo recién cuando
se autorice operar servicios reales.)

Detener también funciona con `Ctrl+C` / `SIGTERM`: la primera señal deja terminar la iteración y
sale limpio (código 7); una segunda señal corta la invocación en curso.

### Códigos de salida

| Código | Significado | Qué hacer |
|---|---|---|
| 0 | Todos los requisitos obligatorios están probados | Nada: proyecto terminado |
| 1 | Error de configuración o árbol de trabajo con cambios ajenos | Leer el mensaje |
| 3 | Ya hay otra instancia corriendo | Esperar o `stop` |
| 4 | Quedan requisitos pero ninguno es ejecutable | Ver `autoloop/INFORME.md` y `BLOCKERS.md` |
| 5 | Límite de uso de la API o presupuesto de la corrida | `resume` más tarde |
| 6 | Iteraciones seguidas sin progreso | Revisar `autoloop/logs/` |
| 7 | Detenido por el usuario (STOP o señal) | `resume` |
| 8 | Se alcanzó `MAX_ITERATIONS` (quedan tareas) | Volver a `start` |
| 9 | `AUTO_COMMIT=0`: cambios esperando revisión manual | Revisar y commitear |

## Qué hace cada iteración

1. Si una iteración anterior quedó cortada (`state/current.json`), guarda sus cambios en `git stash`,
   la registra como `interrumpida` y suma un intento.
2. Exige árbol limpio: si hay cambios que no son del loop, **no arranca** (no pisa trabajo ajeno).
3. Comprueba `STOP`, presupuesto acumulado de la corrida y el control de finalización
   (`tracker.py next`).
4. Arma el prompt con la tarea, el número de intento y el error del intento anterior.
5. Invoca `claude -p` con `timeout`, `--max-budget-usd`, `--permission-mode acceptEdits`, una lista
   de herramientas permitidas y otra de denegadas (push, commit, reset, rm, curl, web…).
6. Interpreta el JSON de salida (costo estimado, error, límite de uso) y `state/last_result.json`.
7. Si hubo cambios: corre `REGRESSION_CMD` y vuelve a ejecutar la prueba declarada en la columna
   Prueba de la tarea. Si algo falla, los cambios van a `git stash` (no se pierden ni se commitean).
8. Registra la iteración en `iterations.jsonl` (número, fechas, duración, tarea, archivos, pruebas,
   resultado, errores, costo, próxima tarea, estado del proyecto) y regenera `PROJECT_STATUS.md`.
9. Commit local (`AUTO_COMMIT=1`). **No hace push** salvo `AUTO_PUSH=1` y rama igual a `PUSH_BRANCH`.
10. Tres fallos en la misma tarea → entrada automática en `BLOCKERS.md` y la tarea queda excluida
    hasta `python3 autoloop/tracker.py attempt --tarea ID --reset`.

## Límites y seguridad (config.env)

| Variable | Defecto | |
|---|---|---|
| `MAX_ITERATIONS` | 5 | Nunca ilimitado (0 o vacío se rechaza) |
| `PAUSE_SECONDS` | 30 | Pausa entre iteraciones (interrumpible) |
| `ITERATION_TIMEOUT` | 1800 | Segundos por invocación |
| `MAX_ATTEMPTS_PER_TASK` | 3 | Luego bloqueo registrado |
| `MAX_NO_PROGRESS` | 2 | Iteraciones seguidas sin cambios útiles |
| `MAX_BUDGET_PER_ITERATION_USD` | 2.00 | Se pasa a `--max-budget-usd` |
| `MAX_BUDGET_PER_RUN_USD` | 8.00 | No arranca otra iteración si podría superarlo |
| `PERMISSION_MODE` | acceptEdits | `bypassPermissions` se rechaza salvo `AUTOLOOP_ALLOW_BYPASS=1` |
| `AUTO_COMMIT` / `AUTO_PUSH` | 1 / 0 | Commit local sí, push no |

El costo es la estimación `total_cost_usd` que reporta Claude Code. Con suscripción Pro/Max el
consumo real se mide contra los límites del plan; el loop detecta el mensaje de límite de uso y se
detiene con código 5 sin gastar intentos.

## Recuperación

Todo el estado está en archivos versionados + `git stash`. Tras un corte (reinicio, kill, límite de
uso) basta con `autoloop/autoloop.sh resume`. Para ver trabajo parcial guardado:
`git stash list | grep autoloop` y `git stash show -p stash@{N}`.

## Programación (opcional, no configurada)

El loop **no** queda corriendo en segundo plano por sí solo. Si se quiere programar:

- **Linux/WSL (cron)**, todos los días a las 03:17, con log:
  ```
  17 3 * * * cd /ruta/al/repo && autoloop/autoloop.sh start --test-mode >> autoloop/logs/cron.log 2>&1
  ```
  El lock evita corridas superpuestas. Requiere la máquina encendida y Claude Code autenticado
  para ese usuario.
- **Windows (Programador de tareas)**: acción `wsl.exe -e bash -lc "cd /mnt/c/ruta/al/repo && autoloop/autoloop.sh start --test-mode"`.
- **GitHub Actions** es posible pero requiere guardar `ANTHROPIC_API_KEY` como secreto y aprobar el
  gasto; no se configuró.
