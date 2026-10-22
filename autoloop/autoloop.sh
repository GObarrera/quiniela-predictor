#!/usr/bin/env bash
# Loop autónomo de desarrollo con Claude Code (modo no interactivo).
#
# Uso:
#   autoloop/autoloop.sh start  [--max-iterations N] [--pause S] [--mock] [--test-mode] [--dry-run]
#   autoloop/autoloop.sh resume [mismas opciones]   # borra autoloop/STOP y arranca
#   autoloop/autoloop.sh stop   [--now]             # detiene al terminar la iteración (o ya, con --now)
#   autoloop/autoloop.sh status                      # estado del proyecto y del proceso
#   autoloop/autoloop.sh report                      # informe de bloqueos -> autoloop/INFORME.md
#   autoloop/autoloop.sh test                        # pruebas del propio loop (sin Claude, sin red)
#
# Códigos de salida:
#   0 proyecto terminado | 1 error de configuración | 3 ya hay otra instancia corriendo
#   4 sin tareas ejecutables (requiere intervención) | 5 límite de uso o presupuesto
#   6 sin progreso | 7 detenido por el usuario | 8 se alcanzó MAX_ITERATIONS
#   9 cambios sin commitear para revisión manual (AUTO_COMMIT=0)
#
# El estado persistente vive en REQUIREMENTS.md, PROJECT_STATUS.md, ROADMAP.md,
# BLOCKERS.md y autoloop/state/. Ninguna invocación de Claude depende de la anterior.
set -uo pipefail

ROOT="${AUTOLOOP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || { echo "autoloop: no estoy dentro de un repositorio git" >&2; exit 1; }
cd "$ROOT" || exit 1

LOOP_DIR="autoloop"
STATE_DIR="$LOOP_DIR/state"
LOG_DIR="$LOOP_DIR/logs"
STOP_FILE="$LOOP_DIR/STOP"
LOCK_FILE="$STATE_DIR/autoloop.lock"
PID_FILE="$STATE_DIR/autoloop.pid"
CURRENT_FILE="$STATE_DIR/current.json"
RESULT_FILE="$STATE_DIR/last_result.json"
ITER_FILE="$STATE_DIR/iterations.jsonl"
REPORT_FILE="$LOOP_DIR/INFORME.md"
TRACKING_FILES="PROJECT_STATUS.md REQUIREMENTS.md ROADMAP.md BLOCKERS.md"

# shellcheck source=config.env
. "$LOOP_DIR/config.env"

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
fi
[ -n "$PY" ] || { echo "autoloop: se necesita Python 3" >&2; exit 1; }

mkdir -p "$STATE_DIR" "$LOG_DIR"

ts()  { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { local m; m="[$(ts)] $*"; echo "$m"; echo "$m" | "$PY" "$LOOP_DIR/redact.py" >> "$LOG_DIR/autoloop.log"; }
tracker() { "$PY" "$LOOP_DIR/tracker.py" --root . --max-intentos "$MAX_ATTEMPTS_PER_TASK" "$@"; }
jget() { "$PY" -c 'import json,sys
try: d=json.load(open(sys.argv[1],encoding="utf-8"))
except Exception: d={}
for k in sys.argv[2].split("."):
    d=d.get(k) if isinstance(d,dict) else None
print("" if d is None else (json.dumps(d,ensure_ascii=False) if isinstance(d,(dict,list)) else d))' "$1" "$2"; }
# Cambios de trabajo (fuera del estado interno del loop).
worktree_changes() { git status --porcelain --untracked-files=all -- . ":(exclude)$STATE_DIR" ":(exclude)$LOG_DIR"; }

# ---------------------------------------------------------------- comandos simples
cmd_stop() {
  touch "$STOP_FILE"
  echo "Pedido de detención registrado ($STOP_FILE). El loop termina al cerrar la iteración actual."
  if [ "${1:-}" = "--now" ] && [ -f "$PID_FILE" ]; then
    local pid; pid="$(cat "$PID_FILE")"
    kill -0 "$pid" 2>/dev/null && { kill -TERM "$pid"; sleep 1; kill -TERM "$pid" 2>/dev/null; echo "Señal enviada al proceso $pid (detención inmediata)."; }
  fi
}

cmd_status() {
  local running=0
  [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null && running=1
  if [ "$running" = 1 ]; then echo "Proceso: CORRIENDO (pid $(cat "$PID_FILE"))"; else echo "Proceso: detenido"; fi
  [ -f "$STOP_FILE" ] && echo "Hay un pedido de detención pendiente ($STOP_FILE). Usá 'resume' para seguir."
  if [ -f "$CURRENT_FILE" ]; then
    if [ "$running" = 1 ]; then echo "Iteración en curso: $(cat "$CURRENT_FILE")"
    else echo "Iteración interrumpida (se recupera al próximo start/resume): $(cat "$CURRENT_FILE")"; fi
  fi
  tracker report | sed -n '3,200p'
}

cmd_report() { tracker report --out "$REPORT_FILE" >/dev/null; echo "Informe escrito en $REPORT_FILE"; cat "$REPORT_FILE"; }

# ---------------------------------------------------------------- bloqueo de instancia única
acquire_lock() {
  if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    flock -n 9 || return 1
  else  # Git Bash en Windows no trae flock: lock por directorio con detección de pid muerto
    if ! mkdir "$LOCK_FILE.d" 2>/dev/null; then
      local old; old="$(cat "$LOCK_FILE.d/pid" 2>/dev/null)"
      if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then return 1; fi
      rm -rf "$LOCK_FILE.d"; mkdir "$LOCK_FILE.d" || return 1
    fi
    echo $$ > "$LOCK_FILE.d/pid"
  fi
  echo $$ > "$PID_FILE"
}
release_lock() { rm -f "$PID_FILE"; rm -rf "$LOCK_FILE.d"; }

# ---------------------------------------------------------------- señales
STOP_REQUESTED=0
CHILD_PID=""
on_signal() {
  if [ "$STOP_REQUESTED" = 1 ] && [ -n "$CHILD_PID" ]; then
    log "Segunda señal: cortando la invocación en curso (pid $CHILD_PID)."
    kill -TERM "$CHILD_PID" 2>/dev/null
  else
    STOP_REQUESTED=1
    log "Señal recibida: se detiene al terminar la iteración actual (otra señal = corte inmediato)."
  fi
}
# Ejecuta en segundo plano y espera, para que las señales se atiendan mientras corre.
run_child() {
  "$@" & CHILD_PID=$!
  local rc
  while :; do
    wait "$CHILD_PID"; rc=$?
    kill -0 "$CHILD_PID" 2>/dev/null || break
  done
  CHILD_PID=""
  return "$rc"
}
pause() {
  local s="$1"
  while [ "$s" -gt 0 ] && [ "$STOP_REQUESTED" = 0 ] && [ ! -f "$STOP_FILE" ]; do sleep 1 & wait $!; s=$((s - 1)); done
}

# ---------------------------------------------------------------- registro
next_iteration_number() {
  "$PY" -c 'import sys,json
n=0
try:
    for l in open(sys.argv[1],encoding="utf-8"):
        try: n=max(n,int(json.loads(l).get("iteracion",0)))
        except Exception: pass
except FileNotFoundError: pass
print(n+1)' "$ITER_FILE"
}

# record <json de campos>  -> agrega una línea al historial (redactada)
record() {
  printf '%s' "$1" | "$PY" -c 'import json,sys
sys.path.insert(0,sys.argv[2])
from redact import redactar
d=json.loads(sys.stdin.read())
with open(sys.argv[1],"a",encoding="utf-8") as f:
    f.write(redactar(json.dumps(d,ensure_ascii=False))+"\n")' "$ITER_FILE" "$LOOP_DIR"
}

run_cost() {  # costo acumulado de esta corrida
  "$PY" -c 'import sys,json
t=0.0
try:
    for l in open(sys.argv[1],encoding="utf-8"):
        try:
            d=json.loads(l)
            if d.get("run_id")==sys.argv[2]: t+=float(d.get("costo_usd") or 0)
        except Exception: pass
except FileNotFoundError: pass
print(f"{t:.4f}")' "$ITER_FILE" "$RUN_ID"
}

append_blocker() {  # append_blocker <tarea> <motivo>
  {
    echo ""
    echo "### AUTO-$1 — tarea $1 excluida tras $MAX_ATTEMPTS_PER_TASK intentos fallidos ($(ts))"
    echo ""
    echo "- Estado: abierto"
    echo "- Causa probable / último error: $2"
    echo "- Acción requerida: revisar los logs (autoloop/logs/) y el historial; corregir la causa y luego"
    echo "  \`$PY autoloop/tracker.py attempt --tarea $1 --reset\` para que el loop la vuelva a tomar."
  } | "$PY" "$LOOP_DIR/redact.py" >> BLOCKERS.md
}

commit_all() {  # commit_all <mensaje>
  [ "$AUTO_COMMIT" = 1 ] || return 0
  git add -A >/dev/null 2>&1   # logs/ y archivos efímeros están en .gitignore
  git diff --cached --quiet && return 0
  git commit -q -m "$1" || { log "ERROR: falló git commit"; return 1; }
  if [ "$AUTO_PUSH" = 1 ]; then
    local br; br="$(git rev-parse --abbrev-ref HEAD)"
    if [ -n "$PUSH_BRANCH" ] && [ "$br" = "$PUSH_BRANCH" ]; then
      git push -q -u origin "$br" || log "AVISO: falló git push (los cambios quedan commiteados localmente)"
    else
      log "AVISO: AUTO_PUSH=1 pero la rama actual ($br) no es PUSH_BRANCH ('$PUSH_BRANCH'); no se pushea."
    fi
  fi
}

finish_records() {  # actualiza PROJECT_STATUS.md e informe y los commitea
  tracker render >/dev/null 2>&1
  tracker report --out "$REPORT_FILE" >/dev/null 2>&1
  commit_all "$1"
}

# Una iteración anterior se cortó (reinicio, kill, corte de luz): preservar y registrar.
recover_interrupted() {
  [ -f "$CURRENT_FILE" ] || return 0
  local it task
  it="$(jget "$CURRENT_FILE" iteracion)"; task="$(jget "$CURRENT_FILE" tarea)"
  log "Recuperando iteración $it interrumpida (tarea $task)."
  local stash_note="sin cambios parciales"
  if [ -n "$(worktree_changes)" ]; then
    git stash push -q -u -m "autoloop: iteración $it interrumpida ($task)" -- . ":(exclude)$STATE_DIR" \
      && stash_note="cambios parciales guardados en git stash ('autoloop: iteración $it interrumpida')"
  fi
  local n; n="$(tracker attempt --tarea "$task")"
  [ "$n" -ge "$MAX_ATTEMPTS_PER_TASK" ] && append_blocker "$task" "iteraciones interrumpidas repetidamente"
  record "$("$PY" -c 'import json,sys; print(json.dumps({"iteracion":int(sys.argv[1]),"run_id":sys.argv[2],"inicio":sys.argv[3],"fin":sys.argv[4],"tarea":sys.argv[5],"resultado":"interrumpida","errores":[sys.argv[6]],"costo_usd":0}))' \
    "$it" "recuperacion" "$(jget "$CURRENT_FILE" inicio)" "$(ts)" "$task" "$stash_note")"
  rm -f "$CURRENT_FILE" "$RESULT_FILE"
  finish_records "autoloop: registro de iteración $it interrumpida ($task)"
}

# ---------------------------------------------------------------- iteración
build_prompt() {  # build_prompt <json tarea> <iteración> <intento> <nota> > archivo
  "$PY" - "$LOOP_DIR/prompt.md" "$1" "$2" "$3" "$MAX_ATTEMPTS_PER_TASK" "$TEST_MODE" "$4" <<'PYEOF'
import json, sys
plantilla, tarea, it, intento, maxi, test, nota = sys.argv[1:8]
t = json.loads(tarea)
fila = (f"- ID: {t['id']}\n- Prioridad: {t['prioridad']}\n- Obligatorio: {'Sí' if t['obligatorio'] else 'No'}\n"
        f"- Estado actual: {t['estado']}\n- Depende de: {', '.join(t['depende']) or '-'}\n"
        f"- Descripción: {t['descripcion']}")
modo = ("\n## MODO DE PRUEBA ACTIVO\nNo envíes ninguna comunicación (email, WhatsApp, SMS), no llames APIs externas, "
        "no uses credenciales reales. Usá dobles de prueba (mocks) para cualquier integración.\n") if test == "1" else ""
txt = open(plantilla, encoding="utf-8").read()
for k, v in {"ITERACION": it, "INTENTO": intento, "MAX_INTENTOS": maxi, "TAREA_FILA": fila,
             "TAREA_ID": t["id"], "MODO_PRUEBA": modo, "NOTA_EXTRA": nota}.items():
    txt = txt.replace("{{" + k + "}}", v)
sys.stdout.write(txt)
PYEOF
}

# Corre la prueba declarada en la columna Prueba si es de un tipo conocido (no ejecuta texto arbitrario).
verify_declared_test() {  # verify_declared_test <tarea>
  local cmd
  cmd="$("$PY" -c 'import sys,re
sys.path.insert(0,sys.argv[2])
from tracker import leer_requisitos
from pathlib import Path
r=[x for x in leer_requisitos(Path("REQUIREMENTS.md")) if x["id"]==sys.argv[1]]
if r and r[0]["estado"]=="probado":
    c=r[0]["prueba"].strip("`").strip()
    if re.fullmatch(r"(python3? -m (unittest|pytest)|pytest|bash autoloop/tests/|npm test|npm run test)[\w ./:=\-]*",c): print(c)
    else: print("__NO_EJECUTABLE__")' "$1" "$LOOP_DIR" 2>/dev/null)"
  [ -z "$cmd" ] && return 0                   # la tarea no quedó marcada como probada
  [ "$cmd" = "__NO_EJECUTABLE__" ] && { DECLARED_TEST="(no verificable automáticamente)"; return 0; }
  DECLARED_TEST="$cmd"
  bash -c "$cmd" >> "$LOG_DIR/iter-$ITER_TAG.tests.log" 2>&1
}

run_iteration() {
  local task_json="$1" it="$2"
  local task attempt start start_s note=""
  task="$("$PY" -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$task_json")"
  attempt=$(( $("$PY" -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get(sys.argv[2],0))
except Exception: print(0)' "$STATE_DIR/attempts.json" "$task") + 1 ))
  start="$(ts)"; start_s=$(date +%s)
  ITER_TAG="$(printf '%04d' "$it")"
  local prompt_file="$LOG_DIR/iter-$ITER_TAG.prompt.md" out_file="$LOG_DIR/iter-$ITER_TAG.json"
  local last_err; last_err="$("$PY" -c 'import json,sys
last=None
try:
    for l in open(sys.argv[1],encoding="utf-8"):
        try:
            d=json.loads(l)
            if d.get("tarea")==sys.argv[2]: last=d
        except Exception: pass
except FileNotFoundError: pass
if last and last.get("resultado")!="exitosa": print("; ".join(last.get("errores") or [])[:600])' "$ITER_FILE" "$task")"
  [ -n "$last_err" ] && note="## Intento anterior fallido
Error registrado: $last_err
Evitá repetir el mismo enfoque."
  build_prompt "$task_json" "$it" "$attempt" "$note" > "$prompt_file"

  local -a cmd=("$CLAUDE_BIN" -p "$(cat "$prompt_file")" --output-format json
                --permission-mode "$PERMISSION_MODE"
                --max-budget-usd "$MAX_BUDGET_PER_ITERATION_USD"
                --no-session-persistence)
  [ -n "$CLAUDE_MODEL" ] && cmd+=(--model "$CLAUDE_MODEL")
  # shellcheck disable=SC2206
  local -a allowed disallowed  # listas separadas por coma: las reglas contienen espacios
  IFS=',' read -r -a allowed <<< "$ALLOWED_TOOLS"
  IFS=',' read -r -a disallowed <<< "$DISALLOWED_TOOLS"
  [ "${#allowed[@]}" -gt 0 ] && cmd+=(--allowedTools "${allowed[@]}")
  [ "${#disallowed[@]}" -gt 0 ] && cmd+=(--disallowedTools "${disallowed[@]}")

  log "Iteración $it — tarea $task (intento $attempt/$MAX_ATTEMPTS_PER_TASK)"
  if [ "$DRY_RUN" = 1 ]; then
    log "[dry-run] Prompt en $prompt_file. Comando: ${cmd[0]} -p <prompt> ${cmd[*]:3}"
    return 0
  fi

  printf '{"iteracion": %s, "tarea": "%s", "inicio": "%s", "pid": %s}\n' "$it" "$task" "$start" "$$" > "$CURRENT_FILE"
  rm -f "$RESULT_FILE"
  local raw="$LOG_DIR/.raw-$ITER_TAG"
  AUTOLOOP_TASK_ID="$task" AUTOLOOP_TEST_MODE="$TEST_MODE" \
    run_child timeout --kill-after=30 "$ITERATION_TIMEOUT" "${cmd[@]}" > "$raw" 2> "$raw.err" < /dev/null
  local rc=$?
  cat "$raw" "$raw.err" | "$PY" "$LOOP_DIR/redact.py" > "$out_file"; rm -f "$raw" "$raw.err"

  # --- interpretar la salida de Claude
  local parsed cost is_error rate_limited summary
  parsed="$("$PY" - "$out_file" <<'PYEOF'
import json, re, sys
txt = open(sys.argv[1], encoding="utf-8").read()
d = {}
for linea in [txt] + txt.splitlines():
    try:
        d = json.loads(linea); break
    except ValueError:
        continue
res = str(d.get("result") or "")
rl = bool(re.search(r"(usage limit|rate limit|limit reached|429|overloaded)", txt, re.I)) and (not d or d.get("is_error"))
print(json.dumps({"cost": float(d.get("total_cost_usd") or 0), "is_error": bool(d.get("is_error")) or not d,
                  "subtype": d.get("subtype", ""), "rate_limited": rl, "summary": res[:800]}))
PYEOF
)"
  cost="$(printf '%s' "$parsed" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["cost"])')"
  is_error="$(printf '%s' "$parsed" | "$PY" -c 'import json,sys; print(int(json.load(sys.stdin)["is_error"]))')"
  rate_limited="$(printf '%s' "$parsed" | "$PY" -c 'import json,sys; print(int(json.load(sys.stdin)["rate_limited"]))')"
  summary="$(printf '%s' "$parsed" | "$PY" -c 'import json,sys; d=json.load(sys.stdin); print(d["summary"] or d["subtype"])')"

  if [ -f "$RESULT_FILE" ]; then  # lo escribe el agente: redactarlo antes de leerlo o registrarlo
    "$PY" "$LOOP_DIR/redact.py" < "$RESULT_FILE" > "$RESULT_FILE.tmp" && mv "$RESULT_FILE.tmp" "$RESULT_FILE"
  fi
  local agent_state errors="" resultado tests_run=() changes
  agent_state="$(jget "$RESULT_FILE" estado)"
  [ "$(jget "$RESULT_FILE" tarea)" = "$task" ] || agent_state=""
  changes="$(worktree_changes)"
  local files; files="$(printf '%s\n' "$changes" | sed -E 's/^.{3}//' | grep -v '^$' | head -50)"

  if [ "$rc" = 124 ] || [ "$rc" = 137 ]; then
    resultado="fallida"; errors="timeout tras ${ITERATION_TIMEOUT}s"
  elif [ "$rate_limited" = 1 ]; then
    resultado="limite_uso"; errors="límite de uso/tasa de la API: $summary"
  elif [ "$rc" != 0 ] || [ "$is_error" = 1 ]; then
    resultado="fallida"; errors="claude terminó con código $rc: $summary"
  elif [ -z "$agent_state" ]; then
    resultado="fallida"; errors="el agente no escribió $RESULT_FILE para $task"
  elif [ "$agent_state" = "failed" ]; then
    resultado="fallida"; errors="$(jget "$RESULT_FILE" errores)"
  elif [ -z "$changes" ]; then
    resultado="sin_progreso"; errors="el agente reportó '$agent_state' pero no hubo cambios en el repositorio"
  else
    # Verificación independiente: regresiones + la prueba declarada de la tarea
    : > "$LOG_DIR/iter-$ITER_TAG.tests.log"
    DECLARED_TEST=""
    if bash -c "$REGRESSION_CMD" >> "$LOG_DIR/iter-$ITER_TAG.tests.log" 2>&1; then
      tests_run+=("regresión: OK")
      if verify_declared_test "$task"; then
        [ -n "$DECLARED_TEST" ] && tests_run+=("$DECLARED_TEST: OK")
        case "$agent_state" in done) resultado="exitosa";; partial) resultado="parcial";; blocked) resultado="bloqueada";; *) resultado="parcial";; esac
      else
        tests_run+=("$DECLARED_TEST: FALLA"); resultado="fallida"; errors="la prueba declarada de $task falla (ver logs/iter-$ITER_TAG.tests.log)"
      fi
    else
      tests_run+=("regresión: FALLA"); resultado="fallida"
      errors="las pruebas de regresión fallan: $(tail -5 "$LOG_DIR/iter-$ITER_TAG.tests.log" | tr '\n' ' ' | cut -c1-400)"
    fi
  fi

  # Cambios de una iteración fallida: no se commitean ni se pierden.
  if [ -n "$changes" ] && { [ "$resultado" = fallida ] || [ "$resultado" = limite_uso ] || [ "$resultado" = sin_progreso ]; }; then
    git stash push -q -u -m "autoloop: iteración $it fallida ($task)" -- . ":(exclude)$STATE_DIR" \
      && errors="$errors | cambios guardados en git stash ('autoloop: iteración $it fallida')"
  fi

  case "$resultado" in
    exitosa) tracker attempt --tarea "$task" --reset >/dev/null; NO_PROGRESS=0 ;;
    parcial|bloqueada) NO_PROGRESS=0 ;;
    limite_uso) ;;  # no cuenta como intento: no es culpa de la tarea
    *)
      NO_PROGRESS=$((NO_PROGRESS + 1))
      local n; n="$(tracker attempt --tarea "$task")"
      if [ "$n" -ge "$MAX_ATTEMPTS_PER_TASK" ]; then
        append_blocker "$task" "$errors"
        log "Tarea $task alcanzó $n intentos fallidos: registrada en BLOCKERS.md y excluida."
      fi ;;
  esac

  local status_json; status_json="$(tracker check)"
  local fields
  fields="$("$PY" - "$it" "$RUN_ID" "$start" "$(ts)" "$(( $(date +%s) - start_s ))" "$task" "$attempt" "$resultado" \
      "$files" "$cost" "$errors" "$summary" "$status_json" "$RESULT_FILE" "$MODE" "${tests_run[@]+"${tests_run[@]}"}" <<'PYEOF'
import json, sys
(it, run, ini, fin, dur, tarea, intento, resultado, archivos, costo, errores, resumen, st, rfile, modo), pruebas = sys.argv[1:16], sys.argv[16:]
try:
    ag = json.load(open(rfile, encoding="utf-8"))
except Exception:
    ag = {}
st = json.loads(st)
sig = st.get("siguiente") or {}
print(json.dumps({
    "iteracion": int(it), "run_id": run, "modo": modo, "inicio": ini, "fin": fin, "duracion_s": int(dur),
    "tarea": tarea, "intento": int(intento), "resultado": resultado,
    "archivos": [a for a in archivos.splitlines() if a],
    "pruebas": list(ag.get("pruebas") or []) + pruebas,
    "errores": [e for e in [errores] if e] + [str(e) for e in (ag.get("errores") or [])][:5],
    "costo_usd": round(float(costo), 4), "resumen": resumen[:500],
    "siguiente": sig.get("id") or ag.get("siguiente") or None,
    "estado_proyecto": f"{st.get('obligatorios_probados')}/{st.get('obligatorios')} obligatorios probados",
}, ensure_ascii=False))
PYEOF
)"
  record "$fields"
  LAST_RESULT="$resultado"
  log "Resultado: $resultado | costo estimado US\$ $cost | ${errors:+error: ${errors:0:300}}"
  rm -f "$CURRENT_FILE"

  if [ "$AUTO_COMMIT" != 1 ]; then
    tracker render >/dev/null 2>&1
    return 0
  fi
  finish_records "autoloop: iteración $it — $task ($resultado)"
}

# ---------------------------------------------------------------- loop principal
cmd_start() {
  DRY_RUN=0; MOCK=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --max-iterations) MAX_ITERATIONS="$2"; shift ;;
      --pause) PAUSE_SECONDS="$2"; shift ;;
      --budget) MAX_BUDGET_PER_RUN_USD="$2"; shift ;;
      --mock) MOCK=1 ;;
      --test-mode) TEST_MODE=1 ;;
      --dry-run) DRY_RUN=1 ;;
      *) echo "Opción desconocida: $1" >&2; exit 1 ;;
    esac
    shift
  done
  case "$MAX_ITERATIONS" in ''|*[!0-9]*|0) echo "MAX_ITERATIONS debe ser un entero > 0" >&2; exit 1 ;; esac
  if [ "$MOCK" = 1 ]; then CLAUDE_BIN="$LOOP_DIR/tests/mock_claude.sh"; TEST_MODE=1; fi
  if [ "$TEST_MODE" = 1 ]; then
    DISALLOWED_TOOLS="$DISALLOWED_TOOLS,mcp__*"
  fi
  if [ "$PERMISSION_MODE" = bypassPermissions ] && [ "${AUTOLOOP_ALLOW_BYPASS:-0}" != 1 ]; then
    echo "PERMISSION_MODE=bypassPermissions requiere AUTOLOOP_ALLOW_BYPASS=1 explícito (y un entorno aislado)." >&2; exit 1
  fi
  MODE="real"; [ "$MOCK" = 1 ] && MODE="mock"; [ "$DRY_RUN" = 1 ] && MODE="dry-run"
  [ "$TEST_MODE" = 1 ] && [ "$MODE" = real ] && MODE="real-test-mode"

  for f in $TRACKING_FILES; do [ -f "$f" ] || { echo "Falta $f (ver autoloop/README.md)" >&2; exit 1; }; done
  command -v "$CLAUDE_BIN" >/dev/null 2>&1 || [ -x "$CLAUDE_BIN" ] || { echo "No encuentro '$CLAUDE_BIN'" >&2; exit 1; }
  command -v timeout >/dev/null 2>&1 || { echo "Se necesita 'timeout' (coreutils)" >&2; exit 1; }

  acquire_lock || { echo "Ya hay otra instancia del loop corriendo (pid $(cat "$PID_FILE" 2>/dev/null))." >&2; exit 3; }
  trap release_lock EXIT
  trap on_signal INT TERM

  if [ -f "$STOP_FILE" ]; then
    echo "Existe $STOP_FILE (pedido de detención previo). Usá 'autoloop.sh resume' para continuar." >&2; exit 7
  fi
  [ "$DRY_RUN" = 1 ] || recover_interrupted
  if [ "$DRY_RUN" = 0 ] && [ -n "$(worktree_changes)" ]; then
    echo "El árbol de trabajo tiene cambios que no son del loop. Commitealos o guardalos antes de arrancar" >&2
    echo "(el loop no toca trabajo ajeno):" >&2; worktree_changes >&2; exit 1
  fi

  RUN_ID="run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  NO_PROGRESS=0; LAST_RESULT=""
  log "Inicio $RUN_ID | modo=$MODE | max_iter=$MAX_ITERATIONS | pausa=${PAUSE_SECONDS}s | presupuesto corrida=US\$ $MAX_BUDGET_PER_RUN_USD"
  local i=0 code=8
  while [ "$i" -lt "$MAX_ITERATIONS" ]; do
    if [ "$STOP_REQUESTED" = 1 ] || [ -f "$STOP_FILE" ]; then log "Detenido por pedido del usuario."; code=7; break; fi
    local spent; spent="$(run_cost)"
    if "$PY" -c 'import sys; sys.exit(0 if float(sys.argv[1]) + float(sys.argv[2]) > float(sys.argv[3]) else 1)' \
         "$spent" "$MAX_BUDGET_PER_ITERATION_USD" "$MAX_BUDGET_PER_RUN_USD"; then
      log "Presupuesto: gastado US\$ $spent; otra iteración podría superar US\$ $MAX_BUDGET_PER_RUN_USD. Deteniendo."; code=5; break
    fi
    local next rc
    next="$(tracker next)"; rc=$?
    if [ "$rc" = 0 ]; then log "Todos los requisitos obligatorios están probados. Proyecto terminado."; code=0; break; fi
    if [ "$rc" = 20 ]; then log "No quedan tareas ejecutables: se requiere intervención (ver $REPORT_FILE)."; code=4; break; fi
    if [ "$rc" != 10 ]; then log "Error leyendo REQUIREMENTS.md: $next"; code=1; break; fi
    local task_json; task_json="$(printf '%s' "$next" | "$PY" -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["siguiente"],ensure_ascii=False))')"

    i=$((i + 1))
    if [ "$DRY_RUN" = 1 ]; then run_iteration "$task_json" "$(next_iteration_number)"; code=0; break; fi
    run_iteration "$task_json" "$(next_iteration_number)"

    if [ "$LAST_RESULT" = limite_uso ]; then log "Límite de uso alcanzado. Reanudá más tarde con 'autoloop.sh resume'."; code=5; break; fi
    if [ "$NO_PROGRESS" -ge "$MAX_NO_PROGRESS" ]; then log "$NO_PROGRESS iteraciones seguidas sin progreso. Deteniendo para revisión."; code=6; break; fi
    if [ "$AUTO_COMMIT" != 1 ] && [ -n "$(worktree_changes)" ]; then log "AUTO_COMMIT=0: cambios listos para revisión manual."; code=9; break; fi
    [ "$i" -lt "$MAX_ITERATIONS" ] && pause "$PAUSE_SECONDS"
  done
  [ "$code" = 8 ] && log "Se alcanzó MAX_ITERATIONS=$MAX_ITERATIONS (quedan tareas; no es fin de proyecto)."
  if [ "$DRY_RUN" = 0 ]; then
    finish_records "autoloop: informe de fin de corrida $RUN_ID"
  fi
  log "Fin $RUN_ID | código $code | costo estimado de la corrida US\$ $(run_cost)"
  return "$code"
}

case "${1:-}" in
  start)  shift; cmd_start "$@"; exit $? ;;
  resume) shift; rm -f "$STOP_FILE"; cmd_start "$@"; exit $? ;;
  stop)   shift; cmd_stop "$@" ;;
  status) cmd_status ;;
  report) cmd_report ;;
  test)   exec bash "$LOOP_DIR/tests/run_tests.sh" ;;
  *) sed -n '2,20p' "$0"; exit 1 ;;
esac
