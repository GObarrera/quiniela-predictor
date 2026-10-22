# Informe de la ejecución de prueba real — 2026-10-22

Corrida: `run-20261022T002546Z-11350`, Claude Code 2.1.307 real (no mock), Linux.

```
MAX_ITERATIONS=3 PAUSE_SECONDS=5 MAX_BUDGET_PER_ITERATION_USD=1.50 MAX_BUDGET_PER_RUN_USD=4 \
ITERATION_TIMEOUT=900 autoloop/autoloop.sh start --test-mode
```

| # | Tarea | Duración | Costo est. | Resultado | Qué pasó |
|---|---|---|---|---|---|
| 1 | QP-01 | 117 s | US$ 0.12 | fallida | El agente escribió `tests/test_terminaciones.py` (3 pruebas OK), pero la verificación independiente del loop falló: `REGRESSION_CMD` usaba `unittest discover -t .`, que exige `tests/__init__.py`. Los cambios se guardaron en `git stash` (no se commitearon ni se perdieron); se sumó 1 intento. |
| 2 | QP-01 | 119 s | US$ 0.14 | exitosa | El prompt incluyó el error del intento 1. El agente agregó `tests/__init__.py`, 4 pruebas pasan, la regresión y la prueba declarada pasan; el loop commiteó. |
| — | — | — | — | detenido (código 4) | Sin tareas ejecutables: INM-00 bloqueado (B-001) y el resto depende de él. Se generó `autoloop/INFORME.md`. |

Total estimado: **US$ 0.27**, 2 de 3 iteraciones usadas, ~4 min.

## Comprobado

- Selecciona la tarea desde REQUIREMENTS.md y la actualiza a `probado` con su comando de prueba.
- Verificación independiente: un "probado" no se commitea si la regresión falla.
- Reintento con el error previo en el prompt; contador de intentos y reseteo al tener éxito.
- Registro estructurado en `autoloop/state/iterations.jsonl`; PROJECT_STATUS.md regenerado.
- Detención correcta por bloqueos (no confunde fin de iteración con fin de proyecto).
- Segunda instancia rechazada mientras la primera corría (código 3).
- `status` durante la ejecución.

## Problemas encontrados y corregidos después de la corrida

1. `REGRESSION_CMD` con `-t .` → quitado.
2. `ALLOWED_TOOLS`/`DISALLOWED_TOOLS` se separaban por espacios y las reglas con espacios
   (`Bash(git status:*)`) llegaban partidas a Claude: la regla para `run_tests.sh` no se aplicó y el
   agente no pudo correrla (quedó denegada; el loop la corrió igual en su verificación). Ahora son
   listas separadas por coma, con prueba que verifica los argumentos exactos, y se comprobó con
   Claude real que `Bash(git status:*)` se permite y `Bash(git push:*)` se deniega.
3. `status` mostraba "iteración interrumpida" mientras el proceso seguía vivo → corregido.

Las pruebas del loop (`autoloop/autoloop.sh test`, 38 casos sin red) pasan tras las correcciones.
