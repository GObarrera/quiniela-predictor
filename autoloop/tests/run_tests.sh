#!/usr/bin/env bash
# Pruebas del loop autónomo. No invocan a Claude, no usan red y no tocan el repo real:
# cada escenario corre en un repositorio git temporal con el doble tests/mock_claude.sh.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LOOP_SRC="$(dirname "$HERE")"
PY="${PYTHON:-python3}"
PASS=0; FAIL=0; FAILED=()

echo "== Pruebas unitarias (tracker, redact)"
if out="$("$PY" -m unittest discover -s "$HERE" -p 'test_*.py' 2>&1)"; then PASS=$((PASS + 1)); else FAIL=$((FAIL + 1)); FAILED+=("unitarias"); fi
printf '%s\n' "$out" | tail -3

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fixture() {  # crea un repo temporal y deja su ruta en $R
  R="$WORK/$1"; mkdir -p "$R"
  ( cd "$R" && git init -q && git config user.email loop@test.local && git config user.name loop-test && git config commit.gpgsign false
    mkdir -p autoloop/tests
    cp "$LOOP_SRC"/{autoloop.sh,tracker.py,redact.py,prompt.md,config.env} autoloop/
    cp "$LOOP_SRC"/tests/mock_claude.sh autoloop/tests/
    printf 'autoloop/logs/\nautoloop/STOP\nautoloop/state/autoloop.lock*\nautoloop/state/autoloop.pid\nautoloop/state/current.json\nautoloop/state/last_result.json\nautoloop/state/mock_calls.log\nautoloop/state/mock_args.log\n__pycache__/\n' > .gitignore
    printf '# Estado\n\nNotas.\n' > PROJECT_STATUS.md
    printf '# Roadmap\n' > ROADMAP.md
    printf '# Bloqueos\n' > BLOCKERS.md
    cat > REQUIREMENTS.md <<'EOF'
# Requisitos

| ID | Prioridad | Obligatorio | Estado | Depende de | Prueba | Descripción |
|---|---|---|---|---|---|---|
| A | P0 | Sí | pendiente | - | - | primera |
| B | P1 | Sí | pendiente | A | - | segunda |
| C | P2 | No | pendiente | - | - | opcional |
EOF
    git add -A && git commit -qm init )
}
loop() {  # loop <args...>  (corre en $R con valores de prueba)
  ( cd "$R" && PAUSE_SECONDS="${PAUSE_SECONDS:-0}" MAX_NO_PROGRESS="${MAX_NO_PROGRESS:-5}" \
      REGRESSION_CMD="${REGRESSION_CMD:-test ! -f BROKEN && if [ -d tests ]; then python3 -m unittest discover -s tests -q; fi}" \
      bash autoloop/autoloop.sh "$@" ) > "$R.out" 2>&1
}
nrec()   { [ -f "$R/autoloop/state/iterations.jsonl" ] && wc -l < "$R/autoloop/state/iterations.jsonl" | tr -d ' ' || echo 0; }
ncalls() { [ -f "$R/autoloop/state/mock_calls.log" ] && grep -c "^$1 " "$R/autoloop/state/mock_calls.log" || echo 0; }
estado() { grep "^| $1 |" "$R/REQUIREMENTS.md" | awk -F'|' '{gsub(/ /,"",$5); print $5}'; }
dirty()  { git -C "$R" status --porcelain | cat ; }
check() {  # check <nombre> <condición...>
  local name="$1"; shift
  if "$@"; then PASS=$((PASS + 1)); echo "  ok   $name"
  else FAIL=$((FAIL + 1)); FAILED+=("$name"); echo "  FALLA $name"; sed 's/^/        /' "$R.out" | tail -15; fi
}
eq() { [ "$1" = "$2" ] || { echo "        esperado '$2', obtenido '$1'"; return 1; }; }

echo "== Escenarios de integración (mock, sin red)"

fixture exito; MAX_ITERATIONS=5 loop start --mock; rc=$?
check "camino feliz termina con código 0"      eq "$rc" 0
check "solo se trabajaron A y B (obligatorios)" eq "$(nrec)" 2
check "A y B quedan probados"                  eq "$(estado A)$(estado B)" "probadoprobado"
check "un commit por iteración"                eq "$(git -C "$R" log --oneline | grep -c "autoloop: iteración")" 2
check "árbol limpio al terminar"                eq "$(dirty)" ""
check "PROJECT_STATUS conserva notas y bloque"  grep -q "Notas." "$R/PROJECT_STATUS.md"
check "informe indica TERMINADO"               grep -q "TERMINADO" "$R/autoloop/INFORME.md"
check "registro tiene campos obligatorios"     "$PY" -c 'import json,sys
d=json.loads(open(sys.argv[1]).readline())
need={"iteracion","inicio","tarea","archivos","pruebas","resultado","errores","costo_usd","siguiente","estado_proyecto","duracion_s"}
sys.exit(0 if need<=d.keys() and d["resultado"]=="exitosa" and d["siguiente"]=="B" else 1)' "$R/autoloop/state/iterations.jsonl"
check "reglas con espacios llegan como un solo argumento" bash -c "grep -qx 'Bash(git push:\\*)' '$R/autoloop/state/mock_args.log' && grep -qx 'Bash(git status:\\*)' '$R/autoloop/state/mock_args.log' && grep -qx 'mcp__\\*' '$R/autoloop/state/mock_args.log' && ! grep -qx 'Bash(git' '$R/autoloop/state/mock_args.log'"
check "usa acceptEdits y tope por iteración"   bash -c "grep -qx acceptEdits '$R/autoloop/state/mock_args.log' && grep -qx -- --max-budget-usd '$R/autoloop/state/mock_args.log'"
MAX_ITERATIONS=5 loop start --mock; rc=$?
check "re-ejecutar un proyecto terminado no duplica trabajo" eq "$rc:$(nrec)" "0:2"

fixture limite; MAX_ITERATIONS=1 loop start --mock; rc=$?
check "respeta MAX_ITERATIONS (código 8)"      eq "$rc:$(nrec)" "8:1"
MAX_ITERATIONS=1 loop start --mock; rc=$?
check "reanuda en la tarea siguiente"          eq "$(tail -1 "$R/autoloop/state/iterations.jsonl" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["tarea"])')" "B"

fixture tres; MOCK_BEHAVIOR_A=fail MAX_ITERATIONS=6 loop start --mock; rc=$?
check "tras 3 fallos deja la tarea y detiene por bloqueo (4)" eq "$rc:$(ncalls A)" "4:3"
check "registra el bloqueo en BLOCKERS.md"     grep -q "AUTO-A" "$R/BLOCKERS.md"
check "no pierde los cambios fallidos (stash)" eq "$(git -C "$R" stash list | grep -c 'fallida (A)')" 3
check "no marca A como probado"                eq "$(estado A)" "pendiente"

fixture sinprog; MOCK_BEHAVIOR=noop MAX_NO_PROGRESS=2 MAX_ITERATIONS=5 loop start --mock; rc=$?
check "detecta falta de progreso (6)"          eq "$rc:$(nrec)" "6:2"

fixture regresion; MOCK_BEHAVIOR_A=breaktests MAX_ITERATIONS=1 loop start --mock
check "regresión rota: iteración fallida"      grep -q '"resultado": "fallida"' "$R/autoloop/state/iterations.jsonl"
check "regresión rota: no se commitea probado" eq "$(estado A):$(dirty)" "pendiente:"

fixture prueba_falsa; MOCK_BEHAVIOR_A=faketest REGRESSION_CMD="test ! -f BROKEN" MAX_ITERATIONS=1 loop start --mock
check "prueba declarada que falla invalida 'probado'" eq "$(estado A)" "pendiente"

fixture cuota; MOCK_BEHAVIOR=ratelimit MAX_ITERATIONS=3 loop start --mock; rc=$?
check "límite de uso detiene (5) sin gastar intentos" eq "$rc:$(nrec):$(cat "$R/autoloop/state/attempts.json" 2>/dev/null)" "5:1:"

fixture crash; MOCK_BEHAVIOR=crash MAX_ITERATIONS=1 loop start --mock
check "código de salida != 0 se registra como fallida" grep -q 'código 2' "$R/autoloop/state/iterations.jsonl"

fixture bloq; MOCK_BEHAVIOR_A=blocked MAX_ITERATIONS=5 loop start --mock; rc=$?
check "bloqueo humano: sigue y termina en 4"    eq "$rc:$(estado A):$(ncalls C)" "4:bloqueado:1"
check "informe lista intervenciones"           grep -q "Intervenciones necesarias" "$R/autoloop/INFORME.md"

fixture presupuesto; MAX_BUDGET_PER_ITERATION_USD=0.01 MAX_BUDGET_PER_RUN_USD=0.015 MAX_ITERATIONS=5 loop start --mock; rc=$?
check "respeta el presupuesto de la corrida (5)" eq "$rc:$(nrec)" "5:1"

fixture secretos; MOCK_BEHAVIOR_A=secret MAX_ITERATIONS=1 loop start --mock
check "no deja claves ni datos personales en registros" bash -c "! grep -rE 'sk-ant-a|ghp_a|juan.perez|5555-1234' '$R/autoloop/state' '$R/autoloop/logs'"

fixture sucio; echo x > "$R/ajeno.txt"; MAX_ITERATIONS=1 loop start --mock; rc=$?
check "no arranca con trabajo ajeno sin commitear" eq "$rc:$(ncalls A):$(cat "$R/ajeno.txt")" "1:0:x"

fixture dry; loop start --mock --dry-run; rc=$?
check "dry-run no invoca ni modifica estado"   eq "$rc:$(ncalls A):$(nrec):$(dirty)" "0:0:0:"

fixture bypass; PERMISSION_MODE=bypassPermissions loop start --mock; rc=$?
check "rechaza bypassPermissions por defecto"   eq "$rc:$(ncalls A)" "1:0"

fixture interrumpida; mkdir -p "$R/autoloop/state"
printf '{"iteracion": 1, "tarea": "A", "inicio": "2026-01-01T00:00:00Z", "pid": 1}\n' > "$R/autoloop/state/current.json"
echo parcial > "$R/a_medias.txt"
MAX_ITERATIONS=1 loop start --mock; rc=$?
check "recupera iteración interrumpida y sigue" eq "$(head -1 "$R/autoloop/state/iterations.jsonl" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["resultado"])'):$(nrec)" "interrumpida:2"
check "guarda el trabajo parcial en stash"      eq "$(git -C "$R" stash list | grep -c interrumpida)" 1

fixture concurrencia
( cd "$R" && MOCK_BEHAVIOR=slow MOCK_SLEEP=4 PAUSE_SECONDS=0 MAX_ITERATIONS=3 REGRESSION_CMD=true bash autoloop/autoloop.sh start --mock > "$R.out1" 2>&1; echo $? > "$R.rc1" ) &
sleep 1.5
MAX_ITERATIONS=1 loop start --mock; rc=$?
check "evita procesos duplicados (3)"          eq "$rc" 3
( cd "$R" && bash autoloop/autoloop.sh stop >/dev/null )
wait
check "'stop' termina tras la iteración en curso (7)" eq "$(cat "$R.rc1"):$(nrec)" "7:1"
MAX_ITERATIONS=1 loop start --mock; rc=$?
check "con STOP pendiente 'start' no arranca"  eq "$rc" 7
MAX_ITERATIONS=1 loop resume --mock; rc=$?
check "'resume' continúa"                      eq "$rc:$(nrec)" "8:2"

fixture senal
( cd "$R" && MOCK_BEHAVIOR=slow MOCK_SLEEP=3 PAUSE_SECONDS=0 MAX_ITERATIONS=3 REGRESSION_CMD=true exec bash autoloop/autoloop.sh start --mock > "$R.out1" 2>&1 ) &
pid=$!; sleep 1; kill -TERM "$pid"; wait "$pid"; rc=$?
check "SIGTERM: cierra la iteración y sale (7)" eq "$rc:$(nrec):$(dirty)" "7:1:"

echo
echo "Resultado: $PASS ok, $FAIL fallas"
[ "$FAIL" = 0 ] || { printf '  - %s\n' "${FAILED[@]}"; exit 1; }
